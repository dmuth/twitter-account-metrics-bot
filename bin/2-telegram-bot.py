#!/usr/bin/env python3
# Vim: :set softtabstop=0 noexpandtab tabstop=4


import argparse
import configparser
import datetime, time
import json
import logging as logger
import logging.config
import math
import os
import sys
import time

import dateparser
import schedule
from sqlalchemy.sql.expression import func
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

sys.path.append("lib")
from tables import create_all, get_session, Config, Tweets
import telegram


#
# Parse our arguments
#
parser = argparse.ArgumentParser(description = "Get statistics for recent tweets and replies from an account.")
parser.add_argument("--debug", action = "store_true", help = "Debugging output")
parser.add_argument("--since", type = str, help = "How far back to go in time for each query? Can be a string such as \"one hour ago\", etc. Default: 1 day ago", default = "1 day ago")
parser.add_argument("--interval", type = int, 
	help = "How many seconds to pause between reports? If set to 60 seconds or less, polling will be once/sec. Otherwise polling will be once/min. (Default: 3600)", 
	default = 3600)
args = parser.parse_args()

#
# Set up the logger
#
if args.debug:
	logging.basicConfig(level=logging.DEBUG, format='%(asctime)s: %(levelname)s: %(message)s')
else:
	logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s')

logger.info("Args: {}".format(args))

#
# Set up our Telegram bot
#
logger.info("Setting up our Telegram bot...")
token = os.environ["TELEGRAM_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]
bot = telegram.Bot(token)


#
# Connect to the database
#
session = get_session()


#
# Parse our timestamp and return the time_t.
# This is meant to be called once for each loop so that we get 
# a new value each time.
#
def parse_time(since):

	logger.info("Parsing our timestamp...")
	now = datetime.datetime.now()
	now_time_t = time.mktime(now.timetuple())

	#
	# All times should be in GMT, so we're going to force that here
	#
	start = dateparser.parse(since + " GMT")

	if not start:
		raise Exception("Unable to parse our time string: {}".format(args.since))
	logger.info("Timestamp parsed as: {}".format(start))

	retval = time.mktime(start.timetuple())

	return(retval)


#
# Return the username that we're looking for tweets from
#
def get_username():
	row = session.query(Config).filter(Config.name == "twitter_username").one()
	return(row.value)


#
# Run queries against our database for tweet data
#
# username - The username to search for
# start_time_t - The start of this time period
#
def get_tweet_data(username, start_time_t):

	retval = {}

	retval["username"] = username 

	retval["num_tweets"] = session.query(func.count(Tweets.tweet_id).label("cnt")).filter(
		Tweets.time_t >= start_time_t).first().cnt

	retval["num_tweets_reply"] = session.query(func.count(Tweets.tweet_id
		).label("cnt")).filter(
		Tweets.time_t >= start_time_t).filter(
		Tweets.reply_tweet_id != None).first().cnt

	retval["min_reply_time"] = "n/a"
	retval["max_reply_time"] = "n/a"
	retval["avg_reply_time"] = "n/a"

	#
	# Only make these calculations if we have replies.
	# 
	if retval["num_tweets_reply"]:
		retval["min_reply_time"] = session.query(
			func.min(Tweets.reply_age).label("min")).filter(
			Tweets.time_t >= start_time_t).filter(
			Tweets.reply_tweet_id != None).filter(
			Tweets.reply_age != 0).first().min

		retval["max_reply_time"] = session.query(
			func.max(Tweets.reply_age).label("max")).filter(
			Tweets.time_t >= start_time_t).filter(
			Tweets.reply_tweet_id != None).filter(
			Tweets.reply_age != 0).first().max

		retval["avg_reply_time"] = session.query(
			func.avg(Tweets.reply_age).label("avg")).filter(
			Tweets.time_t >= start_time_t).filter(
			Tweets.reply_tweet_id != None).filter(
			Tweets.reply_age != 0).first().avg
		retval["avg_reply_time"] = round(retval["avg_reply_time"], 2)


	#
	# Get our median reply time by getting all reply ages in sorted order
	# and then 
	#
	rows = session.query(Tweets).filter(
		Tweets.time_t >= start_time_t).filter(
		Tweets.reply_tweet_id != None).filter(
		Tweets.reply_age != 0).order_by(Tweets.reply_age)
	times = []
	for row in rows:
		times.append(row.reply_age)
	num_rows = len(times)

	retval["median_reply_time"] = "n/a"

	#
	# If we have an odd number of rows, this is easy, just grab the middle row.
	# If it's even, we have to grab the two center rows and then average them.
	#
	if num_rows:
		if num_rows % 2:
			index = math.ceil(num_rows / 2) - 1
			retval["median_reply_time"] = times[index]

		else:
			index1 = int(num_rows / 2 - 1)
			index2 = int(num_rows / 2 )
			val1 = times[index1]
			val2 = times[index2]
			avg = (val1 + val2) / 2
			retval["median_reply_time"] = avg

	return(retval)

#
# Our main entry point.
#
def main():

	start_time_t = parse_time(args.since)
	data = get_tweet_data(username, start_time_t)

	message = ("Tweet reply for user: {username}\n"
		+ "Since: {}\n"
		+ "Num Tweets: {num_tweets}\n"
		+ "Num Replies: {num_tweets_reply}\n"
		+ "Min Reply time: {min_reply_time}\n"
		+ "Max reply time: {max_reply_time}\n"
		+ "Avg reply time: {avg_reply_time}\n"
		+ "Median reply time: {median_reply_time}\n"
		).format(args.since, **data)

	# Send reports to Telegram
	logging.info("Sending message to Telegram: {}".format(message.replace("\n", "  ")))
	bot.send_message(chat_id = chat_id, text = message)
	logging.info("Message sent!")


username = get_username()
logger.info("Reporting on Twitter username: {}".format(username))

#
# Schedule main() to run during intervals
#
schedule.every(args.interval).seconds.do(main)
logger.info("Scheduled main() to run every {} seconds, starting first one now...".format(args.interval))
main()


while True:

	logger.info("Waking up in main loop!")
	schedule.run_pending()

	#
	# If we have an interval of less than a minute, we're probably developing,
	# so sleep for only a second.  Otherwise, sleep for a full minute.
	#
	if args.interval <= 60:
		sleep_secs = 1
	else:
		sleep_secs = 60

	logger.info("Going to sleep for {} seconds...".format(sleep_secs))
	time.sleep(sleep_secs)




