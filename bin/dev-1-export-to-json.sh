#!/bin/bash
#
# Script to run the script in dev mode, which will spawn a shell
#

# Errors are fatal
set -e

pushd $(dirname $0)/.. > /dev/null

DEVEL=1 ./bin/run-1-export-to-json.sh $@


