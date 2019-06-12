#!/bin/bash
#
# Entrypoint script to be run in the Docker container
#


# Errors are fatal
set -e

cd /mnt/bin

if test "$DEVEL"
then
	echo "# "
	echo "# Running in development mode."
	echo "# "
	echo "# Your current directiry: $(pwd)"
	echo "# "
	exec /bin/bash

else
	/mnt/bin/0-get-credentials.py

fi


echo "# "
echo "# To run this script"
echo "# "


