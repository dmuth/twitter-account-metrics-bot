#!/bin/bash
#
# Build our Docker container
#

# Errors are fatal
set -e

pushd $(dirname $0)/.. > /dev/null

echo "# "
echo "# Building container..."
echo "# "
docker build . -f bin/Dockerfile-2-backup-tweets -t twitter-metrics-backup-tweets

CMD=""
CMD_E=""

if test "${DEVEL}"
then
	echo "# "
	echo "# Running in development mode..."
	echo "# "
	CMD="${CMD} -e DEVEL=${DEVEL}"

fi

docker run -it ${CMD} -e "S3=${S3}" -v $(pwd):/mnt twitter-metrics-backup-tweets "$@"

