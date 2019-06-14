#!/bin/bash
#
# Entrypoint script to be run in the Docker container
#


# Errors are fatal
set -e

cd /mnt

if test "$DEVEL"
then
	echo "# "
	echo "# Container launched in development mode."
	echo "# "
	echo "# Your current directiry: $(pwd)"
	echo "# "
	echo "# Scripts located in: /mnt/bin/"
	echo "# "
	exec /bin/bash

else
	/mnt/bin/1-fetch-tweets.py $@

fi


