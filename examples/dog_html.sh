#!/bin/sh
echo "<html><head><title>daloader.py matches</title></head><body>" > attribution.html
../daloader.py --query 'dog' --amount 3 --cc-only Y --folder-format 'dog' --output-format '<p><a href="{path}">{filename}</a> as <a href="{url}">{title}</a> licenced under <a href="{license_url}">{license}</a> by <a href="{author_url}">{author}</a></p>' >> ./attribution.html
echo "</body></html>" >> attribution.html
# convert image links to embedded image
sed -i -E "s/<a href=\"([a-z0-9'_\/.-]*\.(jpg|gif|png))\">([^<]*)<\/a>/<img src=\"\1\" alt=\"\3\" title=\"\3\">/g" attribution.html