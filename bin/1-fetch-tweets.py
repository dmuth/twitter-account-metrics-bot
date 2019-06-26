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
import traceback
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
parser.add_argument("--num", type = int, help = "How many tweets to fetch in total (set this to a large number on the first run! Default: 500)", default = 500)
parser.add_argument("--loop", type = int, help = "Loop after sleeping for N seconds")
parser.add_argument("--ignore-max-tweet-id", action = "store_true", help = "Used for development.  Set this to ignore the max tweet ID. This will cause all tweets to be fetched.")
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
		tweets = twitter.get_user_timeline(screen_name = username, count = count, max_id = max_id,
			since_id = kwargs["since_id"], include_rts = False)

	else: 
		tweets = twitter.get_user_timeline(screen_name = username, count = count,
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
			"text": tweet,
			"reply_tweet_id": None,
			}

		#
		# If this tweet was a reply, get the original tweet ID.
		# We'll backfill the details on that tweet after all of our
		# main user's tweets are fetched (possibly during a future run), 
		# since Twitter API calls are limited.
		#
		if row["in_reply_to_status_id"]:
			tweet["reply_tweet_id"] = row["in_reply_to_status_id"]
			tweet["reply_username"] = row["in_reply_to_screen_name"]

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

		for tweet in result["tweets"]:
			row = Tweets(username = tweet["username"], date = tweet["date"],
				time_t = tweet["time_t"], tweet_id = tweet["id"], 
				text = tweet["text"],
				url =tweet["url"], reply_age = 0, 
				reply_tweet_id = tweet["reply_tweet_id"])

			if "reply_username" in tweet:
				row.reply_username = tweet["reply_username"]

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
# Select our tweets that need backfilling and then do so
#
# @param object twitter Our Twitter object
#
# @return an integer with the number of tweet reply-to info rows backfilled
#
def backfill_tweets(twitter):

	retval = 0
	#
	# Get tweets that:
	# - Have a reply_tweet_id (were replies to tweets with that ID)
	# - Don't have a reply error
	# - and don't have a reply_time_t value
	#
	# Those are tweets that we haven't yet tried pulling the originals.
	#
	rows = session.query(Tweets).filter(Tweets.reply_tweet_id != None).filter(
		Tweets.reply_error == None).filter(Tweets.reply_time_t == None)

	for row in rows:

		try: 
			logger.info("Backfilling tweet id=%d" % (row.tweet_id))
			orig = twitter.show_status(id = row.reply_tweet_id)

			rate_limit = twitter.get_lastfunction_header('x-rate-limit-remaining')
			logger.info("twitter_rate_limit_show_status_left=" + rate_limit)

			row.reply_time_t = int(dateutil.parser.parse(orig["created_at"]).timestamp())
			row.reply_username = orig["user"]["screen_name"]
			row.reply_url = url = "https://twitter.com/%s/status/%s" % (
				row.reply_username, row.reply_tweet_id)
			row.reply_age = row.time_t - row.reply_time_t

		except twython.exceptions.TwythonError as e:

			logger.info("Caught this exception: %s" % e)

			if "User has been suspended" in str(e):
				logger.info("Looks like the original user was suspended, so fudge our data")
				row.reply_error = str(e)

			elif "you are not authorized to see this status" in str(e):
				logger.info("Original tweet is by a locked account")
				row.reply_error = str(e)

			elif "No status found" in str(e):
				logger.info("Original status not found, so fudging our data here")
				row.reply_error = str(e)
			
			elif "You have been blocked" in str(e):
				logger.info("Original status author has blocked you")
				row.reply_error = str(e)

			else:
				raise(e)

			#
			# As a note, we're not touching the reply_time_t here,
			# where means tweets we replied to that can't be retrieved
			# won't be included in stats.  It's annoying, but the
			# upside is that the number of accounts that get suspended,
			# tweets that get deleted, etc. are relatively low.
			#

		session.add(row)
		session.commit()

		retval += 1

	return(retval)

	
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
	row = session.query(func.max(Tweets.tweet_id).label("max")).filter(
		Tweets.username == twitter_data["username"]).first()
	if row:
		since_id = row.max
		if args.ignore_max_tweet_id:
			since_id = None


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

	print("# ")
	print("# Now backfilling reply info on any tweets that are replies.")
	print("# We do this at the end because Twitter has low API limits.")
	print("# ")

	num_tweets_backfilled = backfill_tweets(twitter)
	logger.info("total_tweets_backfilled=%d" % num_tweets_backfilled)

	#
	# Turns out that when this is run as a service in systemd with output redirected, 
	# it is not flushed regularly, and stopping the service loses the output.  Awesome!
	#
	sys.stdout.flush()

# End of main()



if not args.loop:
	try:
		main(args)
	except Exception as e:
		traceback.print_exc()
		sys.exit(1)

else:
	while True:
		try:
			main(args)
		except Exception as e:
			traceback.print_exc()


		logger.info("Sleeping for %d seconds..." % args.loop)
		time.sleep(args.loop)
		logger.info("Waking up!")



