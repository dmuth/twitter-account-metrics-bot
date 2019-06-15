#!/bin/bash
#
# Back up our database to S3.
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
fi

exec /mnt/bin/2-backup-tweets.sh $@


