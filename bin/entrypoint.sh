#!/bin/bash
#
# Entrypoint script for our Docker containers.
# It will either run an interactive bash shell or run a specific script
# as specified by the argument.
#


# Errors are fatal
set -e

cd /mnt

if test "$1" == "bash"
then
	echo "# "
	echo "# Container launched in development mode."
	echo "# "
	echo "# Your current directiry: $(pwd)"
	echo "# "
	echo "# Scripts located in: /mnt/bin/"
	echo "# "
	exec /bin/bash

elif test "$1" == "0-get-credentials"
then
	exec /mnt/bin/0-get-credentials.py

elif test "$1" == "1-fetch-tweets"
then
	shift
	exec /mnt/bin/1-fetch-tweets.py $@

elif test "$1" == "1-export-to-json"
then
	shift
	exec /mnt/bin/1-export-to-json.py $@

elif test "$1" == "2-telegram-bot"
then

	if test ! "$TELEGRAM_CHAT_ID"
	then
		echo "! "
		echo "! Env varaible TELEGRAM_CHAT_ID is not set!"
		echo "! Please set it and re-run this script."
		echo "! "
		echo "! Instructions for getting the Chat ID are in the README"
		echo "! "
		exit 1
	fi

	if test ! "$TELEGRAM_TOKEN"
	then
		echo "! "
		echo "! Env varaible TELEGRAM_TOKEN is not set!"
		echo "! Please set it and re-run this script."
		echo "! "
		echo "! You can get the token by talking to @BotFather on Telegram."
		echo "! "
		exit 1
	fi

	shift
	exec /mnt/bin/2-telegram-bot.py $@

elif test "$1" == "2-backup-tweets"
then
	shift
	exec /mnt/bin/2-backup-tweets.sh $@

else 

	if test "$1"
	then
		echo "! "
		echo "! Unknown arguments: $@"
		echo "! "

	else
		echo "! "
		echo "! No arguments specified to entrypoint script!"
		echo "! "
	fi

	exit 1

fi


