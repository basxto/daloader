#!/usr/bin/python3
import os
import sys
import argparse
import requests
import urllib.request
import re
import html
import configparser
import http.cookiejar
import lxml.html
import lxml.html.clean
import cssselect

cookies = {
    'auth': '',
    'auth_secure': '',
    'userinfo': ''
}

ccRegex = re.compile(r'/(by[a-z\-]*)/')
ccVerRegex = re.compile(r'\d\.\d')
specialChars = re.compile(r'[^\w\.\'\-]+')
urlRegex = re.compile(r'https?://([\w\-]+|commons).(deviantart|wikimedia|sexstories).(com|org)/.*')
daRegex = re.compile(r'https?://([\w\-]+).deviantart.com/([\w\-]+).*')
# allows anchor links
wikicommonsRegex = re.compile(r'https?://commons.wikimedia.org/wiki/(?:.*#.*)?File:(.+)(?:\?.*)?')
storyRegex = re.compile(r'.*')
sscRegex = re.compile(r'https?://www.sexstories.com/(story|search)/([0-9]+)(/?.*)')
sscRelRegex = re.compile(r'(/story/[0-9]*/?[^"]*)')
rssLinks = re.compile(r'<guid isPermaLink="true">(.*?)</guid>')
htmlLinks = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>')
sscTitleRegex = re.compile(r'<h2>([^<>]*)<span', re.MULTILINE)
sscAuthorRegex = re.compile(r'by\s*<a\s+href="(/profile[^"]+)">([^<>]+)</a', re.MULTILINE)
sscDescriptionRegex = re.compile(r'CONTENT\s*-->\s*<div class="block_panel[a-zA-Z0-9_\s]*?">(.*)<!--\s*VOTES', re.MULTILINE)
multiWhitespace = re.compile(r'\s\s+')
multiNewline = re.compile('\n\n\n+')
breakRegex = re.compile(r'(</p>|<br\s?/?>)')
tagRegex = re.compile(r'<.*?>')
galleryTitleRegex = re.compile(r'<span class="folder-title">([^<]*)</span>')
#jpg from http://bla.bla/bla/bla.jpg?blub&blub
filextRegex = re.compile(r'[^\?]*\.([a-z]+)(\?.*)?')

def stringToBool(str):
    return str and ( str.upper() == 'YES' or str.upper() == 'TRUE' or str.upper() == 'ON' or str.upper() == 'Y' or str == '1')

def downloadFile(dirname, fullPath, url):
    # create folders
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    # download image
    if not os.path.exists(fullPath) or args.force.lower() != 'no':
        urllib.request.urlretrieve(url, fullPath)
    else:
        sys.stderr.write('Skipped already existing content "{}" -> "{}"\n'.format(url,fullPath))

def downloadStory(content, fullPath, url, title, author, license):
    if not os.path.exists(fullPath) or args.force.lower() != 'no':
        # remove too much whitespace
        content = multiWhitespace.sub(' ', content)
        # replace breaks
        content = breakRegex.sub('\n', content)
        # remove HTML tags
        content = tagRegex.sub('', content)
        # unescape escaped characters
        content = html.unescape(content)
        # remove too many line breaks
        content = multiNewline.sub('\n\n', content)
        if args.verbose and args.verbose.lower()[0] == 'v':
            sys.stderr.write('Debug: deviation filtered content:\n {}\n'.format(content))
        if args.regex != "no":
            regmatch = storyRegex.search(content)
            if args.verbose and args.verbose.lower() == 'v':
                sys.stderr.write('Debug: regmatch:\n {}\n'.format(regmatch))
            if not regmatch:
                sys.stderr.write('Skipped "{}" because regex doesn\'t match\n'.format(url))
                return False
        # write file
        file = open(fullPath, 'w')
        if stringToBool(args.header):
            file.write('{}\n\n"{}" by {} under {}\n\n'.format(url, title, author, license))
        file.write(content)
    else:
        sys.stderr.write('Skipped already existing content "{}" -> "{}"\n'.format(url,fullPath))
    return True


# return False for error
def downloadDeviation(url):
    # get json representation
    try:
        if args.verbose and args.verbose.lower() != 'no':
            sys.stderr.write('Debug: download {}\n'.format('https://backend.deviantart.com/oembed?url={}'.format(url)))
        deviation = requests.get('https://backend.deviantart.com/oembed?url={}'.format(url)).json()
        if args.verbose and args.verbose.lower()[0] == 'v':
            sys.stderr.write('Debug: oembed deviation:\n {}\n'.format(deviation))
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
        if args.verbose and args.verbose.lower() != 'no':
            sys.stderr.write('Debug: type {}\n'.format(deviation['type']))
        # downloads limited to images and stories
        if deviation['type'] == 'photo':
            if not args.type or args.type.lower() == 'picture':
                # use original file extension
                workFile = '{}.{}'.format(workFile, filextRegex.match(deviation['url'])[1])
                fullPath = os.path.join(dirname, workFile)
                downloadFile(dirname, fullPath, deviation['url'])
            else:
                sys.stderr.write('Type "picture" skipped\n')
                return False
        elif deviation['type'] == 'rich':
            if not args.type or args.type.lower() == 'story':
                workFile = '{}.{}'.format(workFile,'txt')
                fullPath = os.path.join(dirname, workFile)
                # create folders
                if not os.path.exists(dirname):
                    os.makedirs(dirname)
                # download story
                if not os.path.exists(fullPath) or args.force.lower() != 'no':
                    realDeviation = requests.get(url, cookies=cookies).text
                    # make sure we are logged in
                    if deviation['safety'] == 'adult':
                        firstTry = True
                        while realDeviation.find('<span>Log Out</span>') == -1:
                            if not firstTry:
                                sys.stderr.write('Please supply valid cookies and hit enter!\n')
                                input('')
                            else:
                                sys.stderr.write('Reload cookies for mature content "{}"\n'.format(url))
                            loadCookies()
                            realDeviation = requests.get(url, cookies=cookies).text
                            firstTry = False
                    if args.verbose and args.verbose.lower() == 'vv':
                        sys.stderr.write('Debug: html deviation:\n {}\n'.format(realDeviation))
                    # pick description
                    """ content = descriptionRegex.findall(realDeviation.replace('\n',''))
                    if len(content)>0:
                        content = content[0]
                    else:
                        sys.stderr.write('Can’t extract "{}"\n'.format(url,fullPath))
                        return False """
                    tree = lxml.html.fromstring(realDeviation)
                    # clean the source to simplify it
                    cleaner = lxml.html.clean.Cleaner()
                    cleaner.javascript = True
                    cleaner.scripts = True
                    cleaner.comments = True
                    cleaner.style = True
                    cleaner.page_structure = True
                    cleaner.safe_attrs_only = True
                    cleaner.safe_attrs = frozenset(['id','class','data-id','role'])
                    tree = cleaner.clean_html(tree)
                    # remove banner
                    for com in tree.xpath('////header[@role="banner"]'):
                        com.getparent().remove(com)
                    # remove suggestions
                    for com in tree.xpath('////div[@role="complementary"]'):
                        com.getparent().remove(com)
                    # remove parent of comments
                    for com in tree.xpath('////div[@id="comments"]'):
                        com.getparent().getparent().remove(com.getparent())
                    if args.verbose and args.verbose.lower() == 'v':
                        sys.stderr.write('Debug: deviation filtered content:\n {}\n'.format(lxml.html.tostring(tree).decode("utf-8")))
                    # find the match for actual story (new format)
                    richMatches = tree.xpath('////div[@data-id="rich-content-viewer"]')
                    if len(richMatches) != 1:
                        sys.stderr.write('Can’t extract rich text for "{}", {} matches instead of expected 1\n'.format(url,len(richMatches)))
                        richMatches = tree.xpath(cssselect.GenericTranslator().css_to_xpath('div.legacy-journal'))
                        if len(richMatches) != 2:
                            # this can happen if there is no additional description, but we play it safe
                            sys.stderr.write('Can’t extract legacy journal for "{}", {} matches instead of expected 2\n'.format(url,len(richMatches)))
                            return False
                        else:
                            sys.stderr.write('Successfully extracted "{}" as legacy journal instead of rich text\n'.format(url))
                            content = lxml.html.tostring(richMatches[0]).decode("utf-8")
                    else:
                        content = lxml.html.tostring(richMatches[0]).decode("utf-8")

                    if not downloadStory(content, fullPath, url, deviation['title'], deviation['author_name'], license):
                        return False
                else:
                    sys.stderr.write('Skipped already existing content "{}" -> "{}"\n'.format(url,fullPath))
            else:
                sys.stderr.write('Type "story" skipped\n')
                return False
        else:
            sys.stderr.write('Type "{}" not supported\n'.format(deviation['type']))
            return False
    print(args.output_format.format(license=license, license_url=licenseUrl, url=url, author=deviation['author_name'], author_url=deviation['author_url'], title=deviation['title'], deviation=deviation, path=fullPath, folder=dirname, filename=workFile))
    return True

def downloadSsc(url):
    if args.verbose and args.verbose.lower() != 'no':
        sys.stderr.write('Debug: download {}\n'.format(url))
    fullPath = ''
    dirname = ''
    author = 'unknown'
    authorUrl = '#'
    license = 'proprietary'
    licenseUrl = '#'
    try:
        story = requests.get(url).text.replace('\n','')
    except ValueError:
        sys.stderr.write('Failed to parse story "{}"\n'.format(url))
        return False
    title = sscTitleRegex.findall(story)
    if len(title) > 0:
        title = title[0].strip()
    else:
        title = "unknown"
    #print(story)
    authorCombined = sscAuthorRegex.findall(story)
    if len(authorCombined) > 0:
        if len(authorCombined[0]) > 0:
            authorUrl = "https://www.sexstories.com" + authorCombined[0][0]
        if len(authorCombined[0]) > 1:
            author = authorCombined[0][1]
    id = sscRegex.findall(url)
    if len(id) > 0 and len(id[0]) > 1:
        id = id[0][1]
    else:
        sys.stderr.write('Error: "{}" has no story ID\n'.format(url))
        return False
    workFile = specialChars.sub('_', title.lower()) + '-' + id
    # rewrite urls
    url = "https://www.sexstories.com/story/" + id + "/" + specialChars.sub('_', title.lower())
    dirname = specialChars.sub('_', args.folder_format.format(license=license, license_url=licenseUrl, url=url, author=author, author_url=authorUrl, title=title, deviation={}).lower())
    # os.path.exists does not accept empty string
    if dirname == '':
        dirname = '.'
    workFile = '{}.{}'.format(workFile,'txt')
    fullPath = os.path.join(dirname, workFile)
    #print(sscDescriptionRegex.findall(story))
    content = sscDescriptionRegex.findall(story)[0]
    # create folders
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    if not downloadStory(content, fullPath, url, title, author, license):
        return False
    print(args.output_format.format(license=license, license_url=licenseUrl, url=url, author=author, author_url=authorUrl, title=title, deviation={}, path=fullPath, folder=dirname, filename=workFile))
    return True

def downloadWiki(url):
    workFile = wikicommonsRegex.findall(url)[0]
    fullPath = ''
    dirname = ''
    author = 'unknown'
    authorUrl = '#'
    license = 'proprietary'
    licenseUrl = '#'
    metaResponse = requests.get('https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=extmetadata&format=json&titles=File:{}'.format(workFile)).json()
    urlResponse = requests.get('https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=url&format=json&titles=File:{}'.format(workFile)).json()
    # we don't know the page id, but only have one match

    pages = metaResponse['query']['pages']
    for page in pages:
        pageid = page
        if not 'imageinfo' in pages[page]:
            sys.stderr.write('Can\'t get meta data for "{}"\n'.format(url))
            return False
        extmeta = pages[page]['imageinfo'][0]['extmetadata']
    # url of the media file
    if not 'imageinfo' in urlResponse['query']['pages'][pageid]:
        sys.stderr.write('Can\'t get media url for "{}"\n'.format(url))
        return False
    rawUrl = urlResponse['query']['pages'][pageid]['imageinfo'][0]['url']
    if 'LicenseShortName' in extmeta:
        license = extmeta['LicenseShortName']['value']
        # use format of deviantart
        license = license.replace('CC ', '')
    if 'LicenseUrl' in extmeta:
        licenseUrl = extmeta['LicenseUrl']['value']
    if 'Artist' in extmeta:
        if htmlLinks.match(extmeta['Artist']['value']):
            matches = htmlLinks.findall(extmeta['Artist']['value'])
            author = matches[0][1]
            authorUrl = matches[0][0]
            if authorUrl.startswith('//'):
                # fix urls
                authorUrl = 'https:' + authorUrl
        else:
            author = extmeta['Artist']['value']
    # rewrite anchor urls
    url = 'https://commons.wikimedia.org/wiki/File:{}'.format(workFile)
    # define paths
    workFile = specialChars.sub('_', workFile.lower())
    dirname = specialChars.sub('_', args.folder_format.format(license=license, license_url=licenseUrl, url=url, author=author, author_url=authorUrl, title=extmeta['ObjectName']['value'], deviation={}).lower())
    # os.path.exists does not accept empty string
    if dirname == '':
        dirname = '.'
    fullPath = os.path.join(dirname, workFile)
    downloadFile(dirname, fullPath, rawUrl)
    print(args.output_format.format(license=license, license_url=licenseUrl, url=url, author=author, author_url=authorUrl, title=extmeta['ObjectName']['value'], deviation={}, path=fullPath, folder=dirname, filename=workFile))
    return True

def crawl(queryurl):
    matched = 0
    offset = 0
    while matched < int(args.amount):
        if args.verbose and args.verbose.lower() != 'no':
            sys.stderr.write('Debug: crawl {}&offset={}\n'.format(queryurl,offset))
        search = requests.get('{}&offset={}'.format(queryurl,offset)).text
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

def crawlSsc(queryurl):
    matched = 0
    offset = 1
    queryurl = sscRegex.search(queryurl)[3]
    while matched < int(args.amount):
        if args.verbose and args.verbose.lower() != 'no':
            sys.stderr.write('Debug: crawl "{}" based on "{}"\n'.format('https://www.sexstories.com/search/{}{}'.format(offset, queryurl), queryurl))
        search = requests.get('https://www.sexstories.com/search/{}{}'.format(offset, queryurl)).text
        urls = sscRelRegex.findall(search)
        # stop when we get an empty response
        if len(urls) == 0:
            sys.stderr.write('Only {} matches found\n'.format(matched))
            break
        for url in urls:
            if handleUrl('https://www.sexstories.com{}'.format(url.strip())):
                matched+=1
                if matched >= int(args.amount):
                    break
        offset+=1

def handleUrl(url):
    if args.verbose and args.verbose.lower() != 'no':
        sys.stderr.write('Debug: handle {}\n'.format(url))
    if not urlRegex.match(url):
        sys.stderr.write('Skip invalid url "{}"\n'.format(url))
        return False
    if daRegex.match(url):
        matches = daRegex.findall(url)
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
                directory = requests.get(url, cookies=cookies).text
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
    elif sscRegex.match(url):
        if stringToBool(args.no_adult):
            sys.stderr.write('Skip adult content "{}"\n'.format(url))
            return False
        if stringToBool(args.cc_only):
            sys.stderr.write('Skip "{}" sexstory "{}"\n'.format(license, url))
            return False
        matches = sscRegex.findall(url)
        if matches[0][0] == 'story':
            return downloadSsc(url)
        else:
            return crawlSsc(url)
    else:
        sys.stderr.write('Can\'t handle url "{}"\n'.format(url))
        return False
    return True

def loadCookies():
    global cookies
    global args
    global config
    cj = http.cookiejar.MozillaCookieJar()
    # load cookie file into cookies dict
    if args.cookies and os.path.exists(args.cookies):
        cj.load(args.cookies)
        cookies = requests.utils.dict_from_cookiejar(cj)
        if args.verbose and args.verbose.lower() != 'no':
            sys.stderr.write('Debug: load cookies from {}:\n'.format(args.cookies))
        if args.verbose and args.verbose.lower() == 'vv':
            sys.stderr.write(' - {}:\n'.format(cookies))
    elif os.path.exists('cookies.txt'):
        cj.load('cookies.txt')
        cookies = requests.utils.dict_from_cookiejar(cj)
        if args.verbose and args.verbose.lower() != 'no':
            sys.stderr.write('Debug: load cookies from {}:\n'.format('cookies.txt'))
        if args.verbose and args.verbose.lower() == 'vv':
            sys.stderr.write(' - {}:\n'.format(cookies))
    elif os.path.exists('cookies-deviantart-com.txt'):
        cj.load('cookies-deviantart-com.txt')
        cookies = requests.utils.dict_from_cookiejar(cj)
        if args.verbose and args.verbose.lower() != 'no':
            sys.stderr.write('Debug: load cookies from {}:\n'.format('cookies-deviantart-com.txt'))
        if args.verbose and args.verbose.lower() == 'vv':
            sys.stderr.write(' - {}:\n'.format(cookies))
    # load cookies given via config
    if 'deviantart' in config:
        if 'userinfo' in config['deviantart']:
            if args.verbose and args.verbose.lower() != 'no':
                sys.stderr.write('Debug: load userinfo cookie\n')
            cookies['userinfo'] = config['deviantart']['userinfo']
        if 'auth' in config['deviantart']:
            if args.verbose and args.verbose.lower() != 'no':
                sys.stderr.write('Debug: load auth cookie\n')
            cookies['auth'] = config['deviantart']['auth']
        if 'auth_secure' in config['deviantart']:
            if args.verbose and args.verbose.lower() != 'no':
                sys.stderr.write('Debug: load auth_secure cookie\n')
            cookies['auth_secure'] = config['deviantart']['auth_secure']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cookies", help="Full path to cookies.txt file (default: working directory)")
    parser.add_argument("--ini", help="Path to .ini file (default: working directory)")
    parser.add_argument("--url", help="Deviantart site or gallery")
    parser.add_argument("-f", help="Read URLs from file")
    parser.add_argument("--verbose", "-v", default="no", help="Verbose; -vv even more verbose; -vvv even html source and cookie")
    parser.add_argument("--force", default="no", help="Overwrite existing files")
    parser.add_argument("--query", help="Download first matches for search term")
    parser.add_argument("--querysite", default="da", help="da(default),ssc")
    parser.add_argument("--gallery", help="Download first matches of specified user's gallery")
    parser.add_argument("--regex", default="no", help="Regex that has to be in a story")
    parser.add_argument("--favorite", help="Download first matches of specified user's favorites")
    parser.add_argument("--amount", default="20", help="How many matches to download (default is 20)")
    parser.add_argument("--cc-only", help="Only allow deviations licensed under creative commons")
    parser.add_argument("--no-adult", default="yes", help="Only allow deviations, which are not mature content (default)")
    parser.add_argument("--adult-only", help="Only allow adult deviations")
    parser.add_argument("--header", default="yes", help="Put url and title on top of stories (default)")
    parser.add_argument("--type", help="Limit media type (picture, story)")
    parser.add_argument("--folder-format", default="{license}", help="Allowed variables: {license} {license_url} {url} {author} {author_url} {title}")
    parser.add_argument("--output-format", default="[{filename}]({path}) as [{title}]({url}) licenced under [{license}]({license_url}) by [{author}]({author_url})", help="Allowed variables: {license} {license_url} {url} {author} {author_url} {title} {path} {folder} {filename}")
    global cookies
    global storyRegex
    global args
    args = parser.parse_args()
    global config
    config = configparser.RawConfigParser()
    if args.ini:
        config.read(args.ini)
    else:
        config.read('daloader.ini')
    loadCookies()
    
    if args.regex != 'no':
        storyRegex = re.compile(args.regex,re.I)
    
    if args.query:
        if args.querysite == 'ssc':
            sort='relevance'
            theme=''
            crawlSsc('https://www.sexstories.com/search/1/{}/{}//{}//'.format(sort, args.query, theme))
        else:
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
