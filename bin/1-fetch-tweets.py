#!/usr/bin/env python3
# Vim: :set softtabstop=0 noexpandtab tabstop=4


import argparse
import configparser
import datetime
import json
import logging as logger
import logging.config
import sys
import time
import webbrowser

import dateutil.parser
import twython

sys.path.append("lib")
from sqlalchemy.sql.expression import func
from tables import create_all, get_session, Config, Tweets


#
# Parse our arguments
#
parser = argparse.ArgumentParser(description = "Download twitter timeline for a user. Their timeline will be traversed in reverse order and pick up where old fetches left off.")
parser.add_argument("--debug", action = "store_true")
parser.add_argument("--num", type = int, help = "How many tweets to fetch in total (set this to a large number on the first run!)", default = 5)
parser.add_argument("--loop", type = int, help = "Loop after sleeping for N seconds")
args = parser.parse_args()

#
# Set up the logger
#
if args.debug:
	logging.basicConfig(level=logging.DEBUG, format='%(asctime)s: %(levelname)s: %(message)s')
else:
	logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s')

#
# Connect to the database
#
session = get_session()


#
# Fetch a number of tweets from Twitter.
#
# @param object twitter - Our Twitter oject
# @param string username - The username we're looking for tweets from
# @param integer count - How many tweets to fetch?
# @param kwarg max_id - The maximum Id of tweets so we can go back in time
#
# @return A dictionary that includes tweets that aren't RTs, the count, and the last ID.
#
def getTweets(twitter, username, count, **kwargs):

	retval = {"tweets": [], "count": 0, "last_id": -1}
	logger.info(
		"getTweets(): username=%s, count=%d, since_id=%s, last_id=%d" % (
		username, count, kwargs["since_id"], kwargs["last_id"]))
	
	#
	# If we have a last ID use it in the query,
	# otherwise we start at the top of the timeline.
	#
	# Documentation on get_user_timeline() at
	# https://developer.twitter.com/en/docs/tweets/timelines/api-reference/get-statuses-user_timeline
	#
	if ("last_id" in kwargs and kwargs["last_id"]):
		max_id = kwargs["last_id"] - 1
		tweets = twitter.get_user_timeline(user_id = username, count = count, max_id = max_id,
			since_id = kwargs["since_id"], include_rts = False)

	else: 
		tweets = twitter.get_user_timeline(user_id = username, count = count,
			since_id = kwargs["since_id"], include_rts = False)

	for row in tweets:

		tweet_id = row["id"]
		tweet = row["text"]
		user = row["user"]["screen_name"]
		timestamp = int(dateutil.parser.parse(row["created_at"]).timestamp())
		date = datetime.datetime.fromtimestamp(timestamp)
		date_formatted = date.strftime("%Y-%m-%d %H:%M:%S")
		url = "https://twitter.com/%s/status/%s" % (user, tweet_id)

		tweet = {
			"username": user,
			"date": date,
			"date_formatted": date_formatted,
			"time_t": timestamp,
			"id": tweet_id, 
			"url": url,
			"text": tweet
			}

		retval["tweets"].append(tweet)
		retval["count"] += 1

		#
		# The last ID of all tweets, so this could possibly be an RT.
		#
		retval["last_id"] = tweet_id;
		
	return(retval)


#
# Fetch tweets in a series of loops (so we don't exhaust our Twitter API auth rate limit)
# until we hit our max.
#
# @param object twitter Our Twitter object
# @param string username - The username we're looking for tweets from
# @param integer in_num_tweets_left How many tweets to fetch per loop?
# @param integer since_id The highest ID we currently have in the database. 
#	Fetch only tweets greater than this number.
#	This number stays static throughout the run--for a user with no tweets,
#	it will be zero so all possible tweets will be fetched.
#	On future runs, it will be the latest tweet, which means that we'll
#	pickup where we left off, but then traverse the timeline in reverse.
#
# @return tuple A tuple how many tweets were fetched.
#
def getTweetsLoop(twitter, username, in_num_tweets_left, since_id):

	num_tweets_left = in_num_tweets_left
	num_tweets_written = 0
	num_passes_zero_tweets = 3
	num_passes_zero_tweets_left = num_passes_zero_tweets
	last_id = False

	while True:

		result = getTweets(twitter, username, num_tweets_left, 
			last_id = last_id, since_id = since_id)
		rate_limit = twitter.get_lastfunction_header('x-rate-limit-remaining')
		logger.info("twitter_search_rate_limit_left=" + rate_limit)

		num_tweets_left -= result["count"]

		if result["count"] == 0:

			num_passes_zero_tweets_left -= 1
			logger.info("We got zero tweets this pass! passes_left=%d (Are we at the end of the result set?)" % 
				(num_passes_zero_tweets_left))

			if num_passes_zero_tweets_left == 0:
				logger.info("Number of zero passes left == 0. Yep, we're at the end of the result set!")
				break

			continue

		#
		# We got some tweets, reset our zero tweets counter
		#
		num_passes_zero_tweets_left = num_passes_zero_tweets

		logger.info("Tweets fetched=%d, last_id=%s" % (
			result["count"], result.get("last_id", None)))
		logger.info("Tweets left to fetch: %d" % num_tweets_left)

		if "last_id" in result:
			last_id = result["last_id"]

		for row in result["tweets"]:
			row = Tweets(username = row["username"], date = row["date"],
				time_t = row["time_t"], tweet_id = row["id"], text = row["text"],
				url = row["url"], reply_age = 0)
			session.add(row)
			session.commit()

			num_tweets_written += 1

			#
			# If we hit our max number of tweets written, go ahead and bail out!
			#
			if num_tweets_written >= in_num_tweets_left:
				return(num_tweets_written)

	return(num_tweets_written)


#
# Our main function.
#
def main(args):

	#
	# Load our Twitter data
	#
	twitter_data = {}
	results = session.query(Config).filter(Config.name.ilike("twitter%"))
	for row in results:
		key = row.name.replace("twitter_", "")
		twitter_data[key] = row.value

	#
	# Verify our Twitter credentials
	#
	twitter = twython.Twython(twitter_data["app_key"], twitter_data["app_secret"], 
		twitter_data["final_oauth_token"], twitter_data["final_oauth_token_secret"])

	creds = twitter.verify_credentials()
	rate_limit = twitter.get_lastfunction_header('x-rate-limit-remaining')
	logger.info("twitter_rate_limit_verify_credentials_left=" + rate_limit)

	#
	# Who am I, again?
	#
	screen_name = creds["screen_name"]
	logger.info("My screen name is: " + screen_name)

	#
	# Fetch the max ID in the tweets table, which will be our since_id
	# 
	since_id = None
	row = session.query(func.max(Tweets.tweet_id).label("max")).first()
	if row:
		since_id = row.max

	#
	# Actually fetch our tweets.
	#
	print("# ")
	print("# Fetching %d tweets!" % (args.num))
	print("# ")

	(num_tweets_written) = getTweetsLoop(twitter, twitter_data["username"], 
		args.num, since_id)
	logger.info("total_tweets_written_to_db=%d" % (
		num_tweets_written))
	logger.info("ok=1")

	#
	# Turns out that when this is run as a service in systemd with output redirected, 
	# it is not flushed regularly, and stopping the service loses the output.  Awesome!
	#
	sys.stdout.flush()

# End of main()



if not args.loop:
	main(args)

else:
	while True:
		main(args)
		logger.info("Sleeping for %d seconds..." % args.loop)
		time.sleep(args.loop)
		logger.info("Waking up!")



