#!/usr/bin/python3
import os
import sys
import argparse
import requests
import urllib.request
import re

def main():
    ccRegex = re.compile('by-[a-z-]*')
    ccVerRegex = re.compile('[0-9]\.[0-9]')
    specialChars = re.compile('[^a-zA-Z0-9-]+')
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="deviantart site")
    parser.add_argument("--cc-only", help="Only allow deviations licensed under creative commons")
    args = parser.parse_args()
    # get json representation
    deviation = requests.get('https://backend.deviantart.com/oembed?url={}'.format(args.url)).json()
    license = 'proprietary'
    licenseUrl = '#'
    if 'license' in deviation and '_attributes' in deviation['license']:
        license = ccRegex.findall(deviation['license']['_attributes']['href'])[0] + ' ' + ccVerRegex.findall(deviation['license']['_attributes']['href'])[0]
        licenseUrl = deviation['license']['_attributes']['href']
    if license == 'proprietary' and args.cc_only:
        sys.stderr.write("Skip {}, because it's {}\n".format(args.url, license))
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
            if  not os.path.exists(dirname):
                os.makedirs(dirname)
            # download image
            urllib.request.urlretrieve(deviation['url'], fullPath)
            # print markdown attribution
            print('![{}]({}) as [{}]({}) licenced under [{}]({}) by [{}]({})'.format(workFile, fullPath, deviation['title'], args.url, license, licenseUrl, deviation['author_name'], deviation['author_url']))


main()