#!/bin/bash
#
# Script to run the script in dev mode, which will spawn a shell
#

# Errors are fatal
set -e

pushd $(dirname $0)/.. > /dev/null

./bin/run-2-telegram-bot.sh bash


