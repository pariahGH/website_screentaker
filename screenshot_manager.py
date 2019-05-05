from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup
import urllib
import time
import sys
import traceback
import re
import os

exts = [".txt",".pdf",".jpg",".jpeg",".gif",".png",".bmp",".avi",".mov", ".doc",".docx",".xls",".xlsx",".ppt",".pptx",".mp4",".mp3",".wav",".flac",".ogg",".mkv"]

class scraper:
    def __init__(self, driver, base_url):
        self.history = []
        self.driver = driver
        set_width = 1600
        set_height = 2000
        self.base_url = base_url
        self.driver.set_window_size(set_width, set_height)

        directory = 'screenshots'
        full = 'screenshots/full'
        tmp = 'screenshots/tmp'
        if not os.path.exists(directory):
            os.makedirs(directory)
            os.makedirs(full)
            os.makedirs(tmp)
        else:
            if not os.path.exists(full):
                os.makedirs(full)
            if not os.path.exists(tmp):
                os.makedirs(tmp)

    def start(self, url):
        isOurAbsOrRelAndNotCss = lambda x: ("http" not in x or self.base_url in x) and '#' not in x
        try:
            #skip any that are already not our base domain
            if isOurAbsOrRelAndNotCss(url):
                self.driver.get(url)
                #allow time to load page before determining dimensions
                time.sleep(3)
                #check again in case we got a redirect, check if its an rss page, check if its a media extension
                if isOurAbsOrRelAndNotCss(self.driver.current_url) and "rss xmlns:atom" not in self.driver.page_source and not any([(ext in url) for ext in exts]):
                    scrapedUrls = self.parseUrls()
                    #limit filename length
                    self.saveImage(self.driver.title[:100] + ".png")
                    for scrapedUrl in scrapedUrls:
                        #its a relative link, lets re add the base url
                        if "http" not in scrapedUrl:
                            scrapedUrl = self.base_url + scrapedUrl
                        if scrapedUrl not in self.history:
                            self.history.append(scrapedUrl)
                            self.start(scrapedUrl)
        except WebDriverException:
            print(f"Failed processing:{url}")

    def parseUrls(self):
        urls = BeautifulSoup(self.driver.page_source,"html5lib").find_all('a', href=True)
        #check to make sure we are in right domain if it is absolute, or it is relative
        return [url["href"] for url in urls ]

    def saveImage(self, filename):
        yDelta, xDelta, fullWidth, fullHeight, windowHeight = self.getDimensions()
        self.triggerAnimations(fullHeight)
        images = self.processImages(yDelta, xDelta, fullWidth, fullHeight, windowHeight)
        self.stitchScreenshots(images, fullWidth, fullHeight, filename)
        self.clear_tmp()

    def triggerAnimations(self, fullHeight):
        #scroll down the page by the height of the window
        for i in range(0, fullHeight, 800):
            self.driver.execute_script("window.scrollTo(%s,%s)" % (0,i))
            time.sleep(.1)

    def getDimensions(self):
        widths = self.driver.execute_script(
            "return widths = [document.documentElement.clientWidth, document.body ? document.body.scrollWidth : 0, document.documentElement.scrollWidth, document.body ? document.body.offsetWidth : 0, document.documentElement.offsetWidth ]")
        heights = self.driver.execute_script(
            "return heights = [document.documentElement.clientHeight, document.body ? document.body.scrollHeight : 0, document.documentElement.scrollHeight, document.body ? document.body.offsetHeight : 0, document.documentElement.offsetHeight]")
        fullWidth = max(widths)
        fullHeight = max(heights)
        windowWidth = self.driver.execute_script("return window.innerWidth")
        windowHeight = self.driver.execute_script("return window.innerHeight")
        return windowHeight, windowWidth, fullWidth, fullHeight, windowHeight

    def processImages(self, yDelta, xDelta, fullWidth, fullHeight, windowHeight):
        images = []
        #Disable all scrollbars when taking the screenshots
        self.driver.execute_script("document.body.style.overflowY = 'hidden';")
        yPos = 0
        while yPos <= fullHeight:
            self.driver.execute_script("window.scrollTo(%s,%s)" % (0, yPos))
            time.sleep(.5)
            filename = (("screenshots/tmp/screenshot_%s.png") % yPos)
            images.append(filename)
            self.driver.get_screenshot_as_file(filename)
            yPos += yDelta
            #if another full window would take us out of the page
            remainder = fullHeight - yPos
            if yPos + yDelta > fullHeight and remainder > 0:
                #scroll to bottom, take a shot, crop it
                self.driver.execute_script("window.scrollTo(%s,%s)" % (0, fullHeight))
                filename = (("screenshots/tmp/screenshot_%s_temp.png") % yPos)
                self.driver.get_screenshot_as_file(filename)
                base = Image.open(filename)
                #crop is measured from top left
                cropped = base.crop((0, windowHeight - remainder, fullWidth, windowHeight))
                filename = (("screenshots/tmp/screenshot_%s_temp.png") % yPos)
                cropped.save(filename)
                images.append(filename)
        return images

    def stitchScreenshots(self, images, total_width, total_height, filename):
        stitched_image = Image.new('RGB', (total_width, total_height))
        y_offset = 0
        for im in images:
            im = Image.open(im)
            stitched_image.paste(im, (0, y_offset))
            y_offset += im.size[1]
        stitched_image.save(f"screenshots/full/{urllib.parse.quote(filename)}")
        return filename

    def clear_tmp(self):
        #clear tmp folder
        dirPath = 'screenshots/tmp'
        fileList = os.listdir(dirPath)
        for fileName in fileList:
            os.remove(dirPath+"/"+fileName)

if __name__ == '__main__':
    if len(sys.argv)>1:
        url = sys.argv[1]
        driver = webdriver.Chrome(executable_path='./chromedriver_linux64')
        try:
            w = scraper(driver, url)
            w.start(url)
            w.clear_tmp()
        except Exception as exc:
            print(exc)
            traceback.print_exc(file=sys.stdout)
        driver.quit()
    else:
        print("Target url required")