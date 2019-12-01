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

DOCKER_ENV="-e TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}"
DOCKER_ENV="${DOCKER_ENV} -e TELEGRAM_TOKEN=${TELEGRAM_TOKEN}"


ARGS="$@"
if test "$1" == "bash"
then
	ARGS="bash"

else
	ARGS="2-telegram-bot $@"

fi

docker run -it ${DOCKER_ENV} -v $(pwd):/mnt twitter-metrics-telegram-bot ${ARGS}

