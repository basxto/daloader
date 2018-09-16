Download images and stories from deviantart.com

# Features
* Filter out proprietary artwork (no creative commons)
* Filter by type (image, story)
* Filter by safety status (all, adult, non-adult)
* Get URLs from plain text list
* Get URLs via search query
* Output attribution information in terminal

# Example

`./daloader.py --query "pepper carrot" --cc-only yes > attribution.md`

Further examples are located in `examples/`

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