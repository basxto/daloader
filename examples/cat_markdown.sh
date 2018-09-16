#!/bin/sh
../daloader.py --query 'cat' --amount 3 --cc-only Y --folder-format 'cat' --output-format "[{filename}]({path}) as [{title}]({url}) licenced under [{license}]({license_url}) by [{author}]({author_url})" > ./attribution.md
# convert image links to embedded image
sed -i -E "s/^(\[[a-z0-9'_\/.-]*\.(jpg|gif|png)\])/\!\1/g" attribution.md