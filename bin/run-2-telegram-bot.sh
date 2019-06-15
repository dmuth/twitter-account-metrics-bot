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
docker build . -f bin/Dockerfile-2-telegram-bot -t twitter-metrics-telegram-bot

CMD=""
CMD_E=""

if test "${DEVEL}"
then
	echo "# "
	echo "# Running in development mode..."
	echo "# "
	CMD="${CMD} -e DEVEL=${DEVEL}"

fi

docker run -it ${CMD} -v $(pwd):/mnt twitter-metrics-telegram-bot $@

