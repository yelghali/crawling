# -*- coding:utf-8 *-*

#monkey patch
import gevent.monkey
gevent.monkey.patch_all()

import time
import sys
import traceback
from termcolor import colored
import os
import greenlet
import gevent.hub
import gevent.pool
import gevent.queue

import re
import requests
import urllib2

import cookielib
from lxml import etree
import lxml.html


crawled = 0 #crawls counter
ALREADY_CRAWLED = [] #already crawled urls
DATA = [] #contains the clean data to be written


class Handler(object):

    def __init__(self):
        global DATA
        self.output_file =  open("output.csv",'w')
        self.log_file =  open("log.csv", 'w')
        self.cookie_filename = "parser.cookies.txt"

        #simulate browser beahviour with session cookies
        self.cj = cookielib.MozillaCookieJar(self.cookie_filename)
        if os.access(self.cookie_filename, os.F_OK):
            self.cj.load()
        self.opener = urllib2.build_opener(
                urllib2.HTTPRedirectHandler(),
                urllib2.HTTPHandler(debuglevel=0),
                urllib2.HTTPSHandler(debuglevel=0),
                urllib2.HTTPCookieProcessor(self.cj)
                )
        self.opener.addheaders = [
                ('User-agent', ( "Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0" ))
                ]

    def loadPage(self, url, data=None):
        try :
            if data is not None:
                response = self.opener.open(url, data)
            else:
                response = self.opener.open(url)
            res = ''.join(response.readlines())

            print colored("crawl #%s: %s: %s" % (crawled, response.code, url), "yellow")
            self.log(colored("crawl #%s: %s: %s" % (crawled, response.code, url), "yellow"))
            return res
        except:
            print colored("%s loading page failed" % (url), "red")
            traceback.print_stack()

    def addResults(self,data):
        if data and data not in DATA:
            DATA.append(data)
            self.output_file.write(data+'\n')
        self.log_file.write(data+'\n')

    def close(self):
        self.output_file.close()
        self.log_file.close()

    def log(self, data):
        if data:
            self.log_file.write(data+'\n')
#
#main
#

#prepare a pool of workers and a messaging queue
workers_count  = 7
pool = gevent.pool.Pool(workers_count)
queue = gevent.queue.Queue()
#init
start_url_1 = "http://www.hermesbirkinhandbag.com/Hermes_Kelly_1.html"
start_url_2 = "http://www.hermesbirkinhandbag.com/Hermes_Birkin_1.html"
main_domain="http://www.hermesbirkinhandbag.com"

MAX_CRAWLS = 1000
ITEMS_COUNT = 0
def crawler():
    global handler
    global crawled
    global DATA
    global ALREADY_CRAWLED
    global MAX_CRAWLS
    global ITEMS_COUNT

    handler.log("job started...")
    print "job started..."
    while 1:
        try:
            url = queue.get(timeout=1)
            if url in ALREADY_CRAWLED:
                continue
            content = handler.loadPage(url)
            content = content.decode('utf-8')
            doc = lxml.html.fromstring(content)

            imgs = doc.xpath("//div[@class='outletProductImage']/a/img")
            for img in imgs:
                img_url = main_domain + img.attrib['src']
                if img_url:
                    handler.addResults(img_url)
                    ITEMS_COUNT += 1
                    print img_url
                    handler.log(img_url)

            #add the next pages to crawl to the queue
            if crawled < MAX_CRAWLS:
                crawled += 1
                ALREADY_CRAWLED.append(url)

                hrefs = doc.xpath("//div[@class='browsePageControls']/a[@class='control next']")
                for href in hrefs:
                    href = href.attrib['href']
                    if href:
                        next_url = main_domain+href
                        if next_url not in ALREADY_CRAWLED:
                            queue.put(next_url)
                    break #take only the first nav on the top page

            else:
                raise gevent.queue.Empty

        except gevent.queue.Empty:
            break

        print "job done"
        handler.log("job done")
        print "so far crawled %s pages" % crawled
        handler.log("so far crawled %s pages" % crawled)


queue.put(start_url_1)
queue.put(start_url_2)
pool.spawn(crawler)
handler = Handler()

print 'starting Crawler...'
handler.log('starting Crawler...')
while not queue.empty() and not pool.free_count() == workers_count:
    gevent.sleep(0.8)
    for x in xrange(0, min(queue.qsize(), pool.free_count())):
        pool.spawn(crawler)


#wait for jobs to finish
pool.join()
print "Done"
handler.log("Done+\n")
print '\n'
print "collected %s imgs" % ITEMS_COUNT
handler.log("collected %s imgs" % ITEMS_COUNT)
print "see generated output and log files"

handler.close() #close the IO files


