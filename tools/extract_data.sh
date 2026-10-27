#!/bin/zsh
# Pull PLACES / DAYS / EVENTS out of preview/index.html into tools/data.json (uses macOS JavaScriptCore, no node needed)
cd "${0:A:h}/.."
python3 -c "
import re; h=open('preview/index.html').read()
s=re.findall(r'<script>(.*?)</script>',h,re.S)[0]
open('tools/.data.js','w').write(s[:s.index('/* ---------- Time helpers')] + '\nJSON.stringify({PLACES:PLACES,DAYS:DAYS,EVENTS:EVENTS})')
"
osascript -l JavaScript -e "ObjC.import('Foundation'); eval(\$.NSString.stringWithContentsOfFileEncodingError('$PWD/tools/.data.js',4,null).js)" > tools/data.json
rm tools/.data.js
echo "tools/data.json updated"
