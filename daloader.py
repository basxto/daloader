#!/usr/bin/python3
import os
import sys
import argparse
import requests
import urllib.request
import re
import html

ccRegex = re.compile('/(by[a-z\\-]*)/')
ccVerRegex = re.compile('[0-9]\\.[0-9]')
specialChars = re.compile('[^a-zA-Z0-9\'\\-]+')
urlRegex = re.compile('https?://')
rssLinks = re.compile('<guid isPermaLink="true">(.*?)</guid>')
descriptionRegex = re.compile('<div class="text">(.*?)</div>', re.MULTILINE)
scriptRegex = re.compile('<script.*?script>', re.MULTILINE)
multiWhitespace = re.compile('\\s\\s+')
tagRegex = re.compile('<.*?>')

def downloadDeviation(url):
    global ccRegex
    global ccVerRegex
    global specialChars
    global urlRegex
    global args
    if not urlRegex.match(url):
        sys.stderr.write('Skip invalid url "{}"\n'.format(url))
        return False
    # get json representation
    deviation = requests.get('https://backend.deviantart.com/oembed?url={}'.format(url)).json()
    if args.no_adult and deviation['safety'] == 'adult':
        sys.stderr.write('Skip adult content {}\n'.format(url))
        return False
    if args.adult_only and deviation['safety'] == 'nonadult':
        sys.stderr.write('Skip non-adult content {}\n'.format(url))
        return False
    matched = False
    license = 'proprietary'
    licenseUrl = '#'
    if 'license' in deviation and '_attributes' in deviation['license'] and len(deviation['license']['_attributes']['href']) > 0:
        href = deviation['license']['_attributes']['href']
        license = ccRegex.findall(href)[0] + ' ' + ccVerRegex.findall(href)[0]
        licenseUrl = deviation['license']['_attributes']['href']
    if license == 'proprietary' and args.cc_only:
        sys.stderr.write("Skip {} deviation {}\n".format(license, url))
    else:
        # replace all special characters with _
        author = specialChars.sub('_', deviation['author_name'].lower())
        # use original file extension
        workFile = specialChars.sub('_', deviation['title'].lower())
        dirname = os.path.join(license.replace(' ','_'),author)
        if args.no_author_folder:
            dirname = license.replace(' ','_')
        # downloads limited to images and stories
        if deviation['type'] == 'photo' and (not args.type or args.type.lower() == 'photo'):
            # use original file extension
            workFile = '{}.{}'.format(workFile,deviation['url'].split('.')[-1])
            fullPath = os.path.join(dirname, workFile)
            # create folders
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            # download image
            if not os.path.exists(fullPath):
                urllib.request.urlretrieve(deviation['url'], fullPath)
            # print markdown attribution
            print('![{}]({}) as [{}]({}) licenced under [{}]({}) by [{}]({})'.format(workFile, fullPath, deviation['title'], url, license, licenseUrl, deviation['author_name'], deviation['author_url']))
            matched = True
        elif deviation['type'] == 'rich' and (not args.type or args.type.lower() == 'story'):
            workFile = '{}.{}'.format(workFile,'txt')
            fullPath = os.path.join(dirname, workFile)
            # create folders
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            # download image
            if not os.path.exists(fullPath):
                realDeviation = requests.get(url).text
                #print(descriptionRegex.findall(realDeviation))
                # pick description
                content = descriptionRegex.findall(realDeviation.replace('\n',''))[0]
                # remove scripts
                content = scriptRegex.sub('', content)
                # remove too much whitespace
                content = multiWhitespace.sub(' ', content)
                # replace breaks
                content = content.replace('<br />','\n')
                # remove HTML tags
                content = tagRegex.sub('', content)
                # unescape escaped characters
                content = html.unescape(content)
                # write file
                file = open(fullPath, 'w')
                if args.header:
                    file.write('{}\n\n"{}" by {} under {}\n\n'.format(url, deviation['title'], deviation['author_name'], license))
                file.write(content)
            # print markdown attribution
            print('{} as [{}]({}) licenced under [{}]({}) by [{}]({})'.format(fullPath, deviation['title'], url, license, licenseUrl, deviation['author_name'], deviation['author_url']))
            matched = True
    return matched

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Deviantart site")
    parser.add_argument("-f", help="Read URLs from file")
    parser.add_argument("--query", help="Download first matches for search term")
    parser.add_argument("--amount", default="20", help="How many matches to download")
    parser.add_argument("--cc-only", help="Only allow deviations licensed under creative commons")
    parser.add_argument("--no-adult", help="Only allow deviations, which are not mature content")
    parser.add_argument("--adult-only", help="Only allow adult deviations")
    parser.add_argument("--no-author-folder", help="Don't use author folders")
    parser.add_argument("--header", help="Put url and title on top of stories")
    parser.add_argument("--type", help="Limit media type (photo, story)")
    global args
    args = parser.parse_args()
    if args.query:
        matched = 0
        offset = 0
        while matched < int(args.amount):
            search = requests.get('https://backend.deviantart.com/rss.xml?type=deviation&q={}&offset={}'.format(args.query,offset)).text
            urls = rssLinks.findall(search)
            # stop when we get an empty response
            if len(urls) == 0:
                sys.stderr.write('Only {} matches found\n'.format(matched))
                pass
            for url in urls:
                if downloadDeviation(url.strip()):
                    matched+=1
            # deviantart returns 60 matches
            offset+=60
    elif args.f:
        with open(args.f, 'r') as file:
            for url in file:
                downloadDeviation(url.strip())
    elif args.url:
        downloadDeviation(args.url.strip())
    else:
        parser.print_help()



main()