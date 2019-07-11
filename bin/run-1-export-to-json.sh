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
docker build . -f bin/Dockerfile-1-fetch-tweets -t twitter-metrics-fetch-tweets

CMD=""
CMD_E=""

if test "${DEVEL}"
then
	echo "# "
	echo "# Running in development mode..."
	echo "# "
	CMD="${CMD} -e DEVEL=${DEVEL}"

fi

docker run -it ${CMD} -v $(pwd):/mnt twitter-metrics-fetch-tweets export-to-json

