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

ARGS="$@"
if test "$1" == "bash"
then
	ARGS="bash"

else
	ARGS="1-export-to-json $@"

fi

docker run -it -v $(pwd):/mnt twitter-metrics-fetch-tweets ${ARGS}

