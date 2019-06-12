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
docker build . -f bin/Dockerfile-0-get-credentials -t twitter-metrics-get-credentials

CMD=""
CMD_E=""

if test "${DEVEL}"
then
	echo "# "
	echo "# Running in development mode..."
	echo "# "
	CMD="${CMD} -e DEVEL=${DEVEL}"

fi

docker run -it ${CMD} -v $(pwd):/mnt twitter-metrics-get-credentials $@

