#!/usr/bin/python3
import os
import sys
import argparse
import requests
import urllib.request
import re

ccRegex = re.compile('/(by[a-z-]*)/')
ccVerRegex = re.compile('[0-9]\.[0-9]')
specialChars = re.compile('[^a-zA-Z0-9-]+')
urlRegex = re.compile('https?://')
rssLinks = re.compile('<guid isPermaLink="true">(.*?)</guid>')

def downloadDeviation(url, ccOnly, sfwOnly, nsfwOnly):
    global ccRegex
    global ccVerRegex
    global specialChars
    global urlRegex
    if not urlRegex.match(url):
        sys.stderr.write('Skip invalid url "{}"\n'.format(url))
        return
    # get json representation
    deviation = requests.get('https://backend.deviantart.com/oembed?url={}'.format(url)).json()
    if sfwOnly and deviation['safety'] == 'adult':
        sys.stderr.write('Skip adult content {}\n'.format(url))
        return
    if nsfwOnly and deviation['safety'] == 'nonadult':
        sys.stderr.write('Skip non-adult content {}\n'.format(url))
        return
    license = 'proprietary'
    licenseUrl = '#'
    if 'license' in deviation and '_attributes' in deviation['license'] and len(deviation['license']['_attributes']['href']) > 0:
        href = deviation['license']['_attributes']['href']
        license = ccRegex.findall(href)[0] + ' ' + ccVerRegex.findall(href)[0]
        licenseUrl = deviation['license']['_attributes']['href']
    if license == 'proprietary' and ccOnly:
        sys.stderr.write("Skip {} deviation {}\n".format(license, url))
    else:
        # replace all special characters with _
        author = specialChars.sub('_', deviation['author_name'].lower())
        # use original file extension
        workFile = specialChars.sub('_', deviation['title'].lower())
        dirname = os.path.join(license.replace(' ','_'),author)
        fullPath = os.path.join(dirname, workFile)
        # downloads limited to photos for now
        if deviation['type'] == 'photo':
            # use original file extension
            workFile += '.' + deviation['url'].split('.')[-1]
            # create folders
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            # download image
            if not os.path.exists(fullPath):
                urllib.request.urlretrieve(deviation['url'], fullPath)
            # print markdown attribution
            print('![{}]({}) as [{}]({}) licenced under [{}]({}) by [{}]({})'.format(workFile, fullPath, deviation['title'], url, license, licenseUrl, deviation['author_name'], deviation['author_url']))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Deviantart site")
    parser.add_argument("-f", help="Read URLs from file")
    parser.add_argument("--query", help="Download first 60 matches for term")
    parser.add_argument("--offset", default="0", help="Skip x first search entries")
    parser.add_argument("--cc-only", help="Only allow deviations licensed under creative commons")
    parser.add_argument("--no-adult", help="Only allow deviations, which are not mature content")
    parser.add_argument("--adult-only", help="Only allow adult deviations")
    args = parser.parse_args()
    if args.query:
        search = requests.get('https://backend.deviantart.com/rss.xml?type=deviation&q={}&offset={}'.format(args.query,args.offset)).text
        for url in rssLinks.findall(search):
            downloadDeviation(url.strip(), args.cc_only, args.no_adult, args.adult_only)
    elif args.f:
        with open(args.f, 'r') as file:
            for url in file:
                downloadDeviation(url.strip(), args.cc_only, args.no_adult, args.adult_only)
    elif args.url:
        downloadDeviation(url.strip(), args.cc_only, args.no_adult, args.adult_only)
    else:
        parser.print_help()



main()