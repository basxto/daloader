#!/usr/bin/python3
import os
import sys
import argparse
import requests
import urllib.request
import re
import html

ccRegex = re.compile('/(by[a-z\\-]*)/')
ccVerRegex = re.compile('\\d\\.\\d')
specialChars = re.compile('[^\\w/\\.\'\\-]+')
urlRegex = re.compile('https?://([\\w\\-]+).deviantart.com/([\\w\\-]+).*')
wikicommonsRegex = re.compile('https?://commons.wikimedia.org/wiki/File:(.+)')
rssLinks = re.compile('<guid isPermaLink="true">(.*?)</guid>')
htmlLinks = re.compile('<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>')
descriptionRegex = re.compile('<div class="text">(.*?)</div>', re.MULTILINE)
scriptRegex = re.compile('<script.*?script>', re.MULTILINE)
multiWhitespace = re.compile('\\s\\s+')
tagRegex = re.compile('<.*?>')
galleryTitleRegex = re.compile('<span class="folder-title">([^<]*)</span>')

def stringToBool(str):
    return str and ( str.upper() == 'YES' or str.upper() == 'TRUE' or str.upper() == 'ON' or str.upper() == 'Y' or str == '1')

def downloadFile(dirname, fullPath, url):
    # create folders
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    # download image
    if not os.path.exists(fullPath):
        urllib.request.urlretrieve(url, fullPath)

def downloadDeviation(url):
    # get json representation
    try:
        deviation = requests.get('https://backend.deviantart.com/oembed?url={}'.format(url)).json()
    except ValueError:
        sys.stderr.write('Failed to parse deviation "{}"\n'.format(url))
        return False
    if stringToBool(args.no_adult) and deviation['safety'] == 'adult':
        sys.stderr.write('Skip adult content "{}"\n'.format(url))
        return False
    if stringToBool(args.adult_only) and deviation['safety'] == 'nonadult':
        sys.stderr.write('Skip non-adult content "{}"\n'.format(url))
        return False
    license = 'proprietary'
    licenseUrl = '#'
    if 'license' in deviation and '_attributes' in deviation['license'] and len(deviation['license']['_attributes']['href']) > 0:
        href = deviation['license']['_attributes']['href']
        license = ccRegex.findall(href)[0] + ' ' + ccVerRegex.findall(href)[0]
        licenseUrl = deviation['license']['_attributes']['href']

    if license == 'proprietary' and stringToBool(args.cc_only):
        sys.stderr.write('Skip "{}" deviation "{}"\n'.format(license, url))
        return False
    else:
        # get unique name from url
        workFile = specialChars.sub('_', url.split('/')[-1].lower())
        dirname = specialChars.sub('_', args.folder_format.format(license=license, license_url=licenseUrl, url=url, author=deviation['author_name'], author_url=deviation['author_url'], title=deviation['title'], deviation=deviation).lower())
        # os.path.exists does not accept empty string
        if dirname == '':
            dirname = '.'
        fullPath = os.path.join(dirname, workFile)
        # downloads limited to images and stories
        if deviation['type'] == 'photo':
            if not args.type or args.type.lower() == 'picture':
                # use original file extension
                workFile = '{}.{}'.format(workFile,deviation['url'].split('.')[-1])
                fullPath = os.path.join(dirname, workFile)
                downloadFile(dirname, fullPath, deviation['url'])
            else:
                sys.stderr.write('Type "{}" skipped\n'.format(deviation['type']))
                return False
        elif deviation['type'] == 'rich':
            if not args.type or args.type.lower() == 'story':
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
                    if stringToBool(args.header):
                        file.write('{}\n\n"{}" by {} under {}\n\n'.format(url, deviation['title'], deviation['author_name'], license))
                    file.write(content)
            else:
                sys.stderr.write('Type "{}" skipped\n'.format(deviation['type']))
                return False
        else:
            sys.stderr.write('Type "{}" not supported\n'.format(deviation['type']))
            return False
    print(args.output_format.format(license=license, license_url=licenseUrl, url=url, author=deviation['author_name'], author_url=deviation['author_url'], title=deviation['title'], deviation=deviation, path=fullPath, folder=dirname, filename=workFile))
    return True

def downloadWiki(url):
    workFile = wikicommonsRegex.findall(url)[0]
    fullPath = ''
    dirname = ''
    author = 'unknown'
    authorUrl = '#'
    license = 'proprietary'
    metaResponse = requests.get('https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=extmetadata&format=json&titles=File:{}'.format(workFile)).json()
    urlResponse = requests.get('https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=url&format=json&titles=File:{}'.format(workFile)).json()
    # we don't know the page id, but only have one match
    pages = metaResponse['query']['pages']
    for page in pages:
        pageid = page
        extmeta = pages[page]['imageinfo'][0]['extmetadata']
    # url of the media file
    rawUrl = urlResponse['query']['pages'][pageid]['imageinfo'][0]['url']
    license = extmeta['LicenseShortName']['value']
    # use format of deviantart
    license = license.replace('CC ', '')
    if htmlLinks.match(extmeta['Artist']['value']):
        matches = htmlLinks.findall(extmeta['Artist']['value'])
        author = matches[0][1]
        authorUrl = matches[0][0]
    else:
        author = extmeta['Artist']['value']
    # define paths
    workFile = specialChars.sub('_', workFile.lower())
    dirname = specialChars.sub('_', args.folder_format.format(license=license, license_url=extmeta['LicenseUrl']['value'], url=url, author=author, author_url=authorUrl, title=extmeta['ObjectName']['value'], deviation={}).lower())
    # os.path.exists does not accept empty string
    if dirname == '':
        dirname = '.'
    fullPath = os.path.join(dirname, workFile)
    downloadFile(dirname, fullPath, rawUrl)
    print(args.output_format.format(license=license, license_url=extmeta['LicenseUrl']['value'], url=url, author=author, author_url=authorUrl, title=extmeta['ObjectName']['value'], deviation={}, path=fullPath, folder=dirname, filename=workFile))
    return False

def crawl(url):
    matched = 0
    offset = 0
    while matched < int(args.amount):
        search = requests.get('{}&offset={}'.format(url,offset)).text
        urls = rssLinks.findall(search)
        # stop when we get an empty response
        if len(urls) == 0:
            sys.stderr.write('Only {} matches found\n'.format(matched))
            break
        for url in urls:
            if handleUrl(url.strip()):
                matched+=1
                if matched >= int(args.amount):
                    break
        # deviantart returns 60 matches
        offset+=60

def handleUrl(url):
    if urlRegex.match(url):
        matches = urlRegex.findall(url)
        if matches[0][0] == 'www':
            author = matches[0][1]
        else:
            author = matches[0][0]
        if '/art/' in url:
            return downloadDeviation(url.strip())
        elif '/gallery/' in url:
            # check if there's more comming
            if url.split('/')[-2] == 'gallery':
                # all deviations of this author
                meta = 'all'
            else:
                # gallery directory
                directory = requests.get(url).text
                titles = galleryTitleRegex.findall(directory)
                if len(titles) == 0:
                    sys.stderr.write('Can\'t extract title of gallery directory "{}"\n'.format(url))
                    return False
                meta = galleryTitleRegex.findall(directory)[0]
            crawl('https://backend.deviantart.com/rss.xml?type=deviation&q=by:{} sort:time meta:{}'.format(author, meta))
        elif '/favourites/' in url:
            crawl('https://backend.deviantart.com/rss.xml?type=deviation&q=favby:{}'.format(author))
        else:
            sys.stderr.write('Can\'t handle url "{}"\n'.format(url))
    elif wikicommonsRegex.match(url):
        downloadWiki(url)
    else:
        sys.stderr.write('Can\'t handle url "{}"\n'.format(url))
        return False
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Deviantart site or gallery")
    parser.add_argument("-f", help="Read URLs from file")
    parser.add_argument("--query", help="Download first matches for search term")
    parser.add_argument("--gallery", help="Download first matches of specified user's gallery")
    parser.add_argument("--favorite", help="Download first matches of specified user's favorites")
    parser.add_argument("--amount", default="20", help="How many matches to download (default is 20)")
    parser.add_argument("--cc-only", help="Only allow deviations licensed under creative commons")
    parser.add_argument("--no-adult", default="yes", help="Only allow deviations, which are not mature content (default)")
    parser.add_argument("--adult-only", help="Only allow adult deviations")
    parser.add_argument("--header", default="yes", help="Put url and title on top of stories (default)")
    parser.add_argument("--type", help="Limit media type (picture, story)")
    parser.add_argument("--folder-format", default="{license}", help="Allowed variables: {license} {license_url} {url} {author} {author_url} {title}")
    parser.add_argument("--output-format", default="[{filename}]({path}) as [{title}]({url}) licenced under [{license}]({license_url}) by [{author}]({author_url})", help="Allowed variables: {license} {license_url} {url} {author} {author_url} {title} {path} {folder} {filename}")
    global args
    args = parser.parse_args()
    if args.query:
        crawl('https://backend.deviantart.com/rss.xml?type=deviation&q={}'.format(args.query))
    elif args.gallery:
        handleUrl('https://{}.deviantart.com/gallery/'.format(args.gallery))
    elif args.favorite:
        handleUrl('https://{}.deviantart.com/favourites/'.format(args.favorite))
    elif args.f:
        with open(args.f, 'r') as file:
            for url in file:
                handleUrl(url.strip())
    elif args.url:
        handleUrl(args.url)
    else:
        parser.print_help()

main()