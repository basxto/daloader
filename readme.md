**D**igital **a**rtwork down**loader** for deviantart.com, commons.wikimedia.org and sexstories.com

# Features
## General
* Get URLs from plain text list
* Output attribution information in terminal (source URL, author, lincense)

## Deviantart
* Work directly with artwork, favorite or gallery URLs
* Filter out proprietary artwork (no creative commons)
* Filter by type (image, story)
* Filter by safety status (all, adult, non-adult)
* Get URLs via search query
* Cookie support for mature content

# How Deviantart gets accessed
* [RSS API](https://www.deviantart.com/developers/rss) (search, gallery, favorite)
* [oEmbed API](https://www.deviantart.com/developers/oembed) (filters, image extraction)
* Parsing the site (gallery folders, story extraction)

## WikiMedia Commons
* Download videos, animated gifs and image
* Rewrite URLs

## Sexstories.com
* Story extraction via site parsing
* Rewrite URLs

# Example

`./daloader.py --query "pepper carrot" --cc-only yes > attribution.md`
`./daloader.py --query "wallpaper in:photography/abstract" > attribution.md`
`./daloader.py --url https://www.deviantart.com/deevad/gallery/31863052/Comic-Pepper-Carrot --cc-only y > attribution.md`


More information for query syntax at [deviantart](https://www.deviantartsupport.com/en/article/how-do-i-use-rss-feeds)

Example scripts with further processing of the output in `examples/`

# Installation
## Linux
### Install Python
#### Debian / Ubuntu
```sh
# apt-get install python3 python3-pip
```
#### ArchLinux / Manjaro
```sh
# pacman -S python python-pip
```
### Get all dependencies
```sh
# pip3 install requests
```

## Windows
### Install Python
Get [chocolatey](https://chocolatey.org/)

Install via administrator terminal (Windows PowerShell or ConsoleZ)
```sh
# choco install python3
```

### Getting all dependencies
After installing python you  have to restart your terminal, then again with administrator rights do
```sh
# pip3 install requests
```