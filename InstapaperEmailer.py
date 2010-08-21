#!/usr/bin/env python
""" Instapaper Emailer

This script will email you with any new items in your instapaper account
in the unread queue.  Each time you run the script, it will only email
any items that are new from the last time it was run.

I wrote this script because I wanted a way to read my instapaper items
offline.  I run it via cron, and every morning I have my new unread
articles on my phone to read while I don't have service.

Copyright (c) 2010, Jonathan Beluch 
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import cookielib
import urllib
import urllib2
import urlparse
import smtplib
from BeautifulSoup import BeautifulSoup as BS, SoupStrainer as SS
from cPickle import Pickler, Unpickler

#gmail/email settings
HOSTNAME = 'smpt.gmail.com'
USERNAME = 'joe@gmail.com'
PASSWORD = 'password123'
FROM_ADDR = USERNAME 
TO_ADDR = USERNAME

#instapaper settings
IP_USERNAME = 'joe@gmail.com'
IP_PASSWORD = 'password1234'

#script settings
PICKLE_FN = 'pages.pickle'

class InstapaperScraper(object):
    """Scraper for instapaper.com.  Takes a username and password and
    returns a list of all the text-only version urls on your unread 
    page. """ 
    base_url = 'http://www.instapaper.com'
    login_url = 'http://www.instapaper.com/user/login'
    pages_url = 'http://www.instapaper.com/u'

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))

    def scrape(self):
        params = {'username': self.username,
                  'password': self.password}
        self.opener.open(self.login_url, urllib.urlencode(params))
        html = self.opener.open(self.pages_url).read()
        a_tags = BS(html, SS('a', title='Text-only version'))
        return [urlparse.urljoin(self.base_url, a['href']) for a in a_tags]

def sendmail(htmls):
    server = smtplib.SMTP(HOSTNAME)
    #server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(USERNAME, PASSWORD)
    for html in htmls:
        headers = ['From: %s' % FROM_ADDR,
                   'To: %s' % TO_ADDR,
                   'MIME-Version: 1.0',
                   'Content-type: text/html',
                   'Subject: %s' % BS(html, SS('title')).text]
        message = '\r\n'.join(headers).encode('utf-8') + '\r\n' + html 
        server.sendmail(FROM_ADDR, TO_ADDR, message) 
    server.quit() 

def main():
    """This function emails you any new items found in your instapaper
    unread queue.  Each time its run it checks all the online urls
    against a local file which has a list of all the urls from the last
    time the script was run.  This way only new urls are emailed to you.

        Script workflow:

        (1) If there is an existing pickle file, read urls
        (2) Scrape all urls from your instapaper.com account
        (3) Compare the two lists, if there are new urls:
                - Download html contents of new urls and email
        (4) Write the current set of online urls to disk, for reference 
            next time the script is run.
    """
    urls_disk = set()
    try:
        f = open(PICKLE_FN, 'r')
    except IOError, e:
        print 'Cannot find existing pickle file, all pages will be emailed.'
    else:
        up = Unpickler(f)
        urls_disk = up.load()
        f.close()

    #get all of the saved pages on the web
    scraper = InstapaperScraper(IP_USERNAME, IP_PASSWORD)
    urls_online = set(scraper.scrape())

    #get only the items online that are not in the disk set
    urls_new =  urls_online - urls_disk 

    #download the html source for each new page
    new_htmls = [urllib2.urlopen(url).read() for url in urls_new]

    #send email for each of the new pages
    if len(new_htmls) > 0:
        sendmail(new_htmls)
    print 'Emailed %d new pages.' % len(new_htmls)

    #write all of the online urls to disk
    f = open(PICKLE_FN, 'w')
    p = Pickler(f)
    p.dump(urls_online)
    f.close()

if __name__ == '__main__':
    main()
