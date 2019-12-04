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
docker build . -f bin/Dockerfile -t twitter-metrics

ARGS="$@"
if test "$1" == "bash"
then
	ARGS="bash"

else
	ARGS="$@"

fi

docker run -it -v $(pwd):/mnt twitter-metrics ${ARGS}

