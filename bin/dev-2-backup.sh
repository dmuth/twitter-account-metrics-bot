#!/bin/bash
#
# Script to run the script in dev mode, which will spawn a shell
#

# Errors are fatal
set -e

pushd $(dirname $0)/.. > /dev/null

export S3=s3://dmuth-furry-tweets/users/dev/
./bin/run-2-backup-tweets.sh bash


