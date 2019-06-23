#!/bin/bash
#
# Entrypoint script to be run in the Docker container
#


# Errors are fatal
set -e

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


cd /mnt

if test "$DEVEL"
then
	echo "# "
	echo "# Container launched in development mode."
	echo "# "
	echo "# Your current directiry: $(pwd)"
	echo "# "
	echo "# Scripts located in: /mnt/bin/"
	echo "# "
	exec /bin/bash

else
	/mnt/bin/2-telegram-bot.py $@

fi


