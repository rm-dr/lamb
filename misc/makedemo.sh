#!/bin/bash
# Should be run from the misc directory.
# Will not work with any other root.

# Create this file.
# Should define two variables:
# DAV_USER="name:password"
# DAV_URL="https://site.com/dav-path"

if [[ -f "secrets.sh" ]]; then
	source secrets.sh
else
	echo "Cannot run without secrets.sh"
	exit
fi

# Activate venv if not in venv
if [[ "$VIRTUAL_ENV" == "" ]]; then
	source ../venv/bin/activate
fi

# Make sure our venv is running the latest
# version of lamb.
pip install --editable ..


# Make gif
vhs < demo.tape

# Upload
curl \
	--user $DAV_USER \
	--url $DAV_URL \
	--upload-file "lambdemo.gif"
