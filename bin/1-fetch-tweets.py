#!/usr/bin/env python3
# Vim: :set softtabstop=0 noexpandtab tabstop=4


import argparse
import configparser
import datetime
import json
import logging as logger
import logging.config
import os
import sys
import time
import traceback
import webbrowser

import dateutil.parser
import twython

sys.path.append("lib")
import config as configParser
from sqlalchemy.sql.expression import func
from tables import create_all, get_session, Tweets


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
# Turn the data structure we got back from Twitter into something we can use by only 
# pulling out fields which we care about.
#
def parseTweets(tweets):

	retval = []

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

		retval.append(tweet)

	return(retval)


#
# Write our tweets to the database
#
def write_tweets(tweets):

	for tweet in tweets:
		row = Tweets(username = tweet["username"], date = tweet["date"],
			time_t = tweet["time_t"], tweet_id = tweet["id"], 
			text = tweet["text"],
			url =tweet["url"], reply_age = 0, 
			reply_tweet_id = tweet["reply_tweet_id"])

		if "reply_username" in tweet:
			row.reply_username = tweet["reply_username"]

		session.add(row)
		session.commit()

	logger.info("Wrote {} tweets to the database!".format(len(tweets)))


#
# Fetch a number of tweets from Twitter.
#
# @param object twitter - Our Twitter oject
# @param string username - The username we're looking for tweets from
# @param integer count - How many tweets to fetch?
# @param kwarg max_id - Return tweets less than or equal to this ID. Used when paging through old tweets.
# @param kwarg min_id - Return tweets after this ID. Used when looking for new tweets.
#
# @return A dictionary that includes tweets that aren't RTs, the count, and the last ID.
#
def getTweets(twitter, username, count, **kwargs):

	if not "min_id" in kwargs:
		kwargs["min_id"] = None
	if not "max_id" in kwargs:
		kwargs["max_id"] = None

	retval = {"tweets": [], "count": 0, "min_id": -1}
	logger.info(
		"getTweets(): username=%s, count=%d, min_id=%s, max_id=%s" % (
		username, count, kwargs["min_id"], kwargs["max_id"]))
	
	#
	# If we have a last ID use it in the query,
	# otherwise we start at the top of the timeline.
	#
	# Documentation on get_user_timeline() at
	# https://developer.twitter.com/en/docs/tweets/timelines/api-reference/get-statuses-user_timeline
	# https://developer.twitter.com/en/docs/tweets/timelines/guides/working-with-timelines
	#
	if kwargs["min_id"] is None and kwargs["max_id"] is None:
		logger.info("No since_id or max_id, fetch just one tweet to prime our table.")
		tweets = twitter.get_user_timeline(screen_name = username, count = count, 
			include_rts = False)

	elif kwargs["max_id"] is not None:
		logger.info("A max_id of {} was specified, fetching {} tweets before that".format(
			kwargs["max_id"], count))
		tweets = twitter.get_user_timeline(screen_name = username, count = count, 
			max_id = kwargs["max_id"] - 1,
			include_rts = False)

	elif kwargs["min_id"] is not None:
		logger.info("A min_id of {} was specified, fetching {} tweets after that".format(
			kwargs["min_id"], count))
		tweets = twitter.get_user_timeline(screen_name = username, count = count, 
			since_id = kwargs["min_id"],
			include_rts = False)

	#
	# Parse our tweets to get values we care about, and return some metadata as well.
	#
	retval["tweets"] = parseTweets(tweets)
	retval["count"] = len(tweets)
	if len(retval["tweets"]):
		retval["min_id"] = retval["tweets"][len(tweets) - 1]["id"]

	rate_limit = twitter.get_lastfunction_header('x-rate-limit-remaining')
	logger.info("twitter_search_rate_limit_left=" + rate_limit)

	return(retval)


#
# Look up the supplied error we got when trying to backfill a tweet.
# This is mostly to print up useful messages via logger.info(),
# as seeing the phrase "suspended" can make people running this app nervous. :-)
#
def backfill_tweets_lookup_error(e):

	if "User has been suspended" in str(e):
		logger.info("Looks like the original user was suspended, so fudge our data")
		return(str(e))

	elif "you are not authorized to see this status" in str(e):
		logger.info("Original tweet is by a locked account")
		return(str(e))

	elif "No status found" in str(e):
		logger.info("Original status not found, so fudging our data here")
		return(str(e))
			
	elif "You have been blocked" in str(e):
		logger.info("Original status author has blocked you")
		return(str(e))

	elif "Twitter API returned a 404" in str(e):
		logger.info("Twitter's API returned a 404")
		return(str(e))

	else:
		raise(e)


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
	#
	# For testing, you can get tweets to backfill with this query:
	# UPDATE tweets SET reply_error=null, reply_time_t=null WHERE id IN ( SELECT id FROM tweets WHERE reply_error != '' LIMIT 3);
	#
	rows = session.query(Tweets).filter(Tweets.reply_tweet_id != None).filter(
		Tweets.reply_error == None).filter(Tweets.reply_time_t == None)

	logger.info("tweets_to_backfill={}".format(rows.count()))

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
			row.reply_error = backfill_tweets_lookup_error(e)

			rate_limit = twitter.get_lastfunction_header('x-rate-limit-remaining')
			logger.info("twitter_rate_limit_show_status_left=" + rate_limit)

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
# Verify our Twitter credentials are still valid.
#
# Returns the Twiter object with credentials loaded into it.
#
def verify_twitter_credentials(config):

	twitter = twython.Twython(config.get("twitter_app_key"), config.get("twitter_app_secret"),
		config.get("final_oauth_token"), config.get("final_oauth_token_secret"))

	creds = twitter.verify_credentials()
	rate_limit = twitter.get_lastfunction_header('x-rate-limit-remaining')
	logger.info("twitter_rate_limit_verify_credentials_left=" + rate_limit)

	screen_name = creds["screen_name"]
	logger.info("My screen name is: " + screen_name)

	return(twitter)


#
# Return the maximum Tweet ID or None if there are no tweets.
#
def get_max_tweet_id(session, username):

	retval = None
	row = session.query(func.max(Tweets.tweet_id).label("max")).filter(
		Tweets.username == username).first()

	if row:
		retval = row.max

	return(retval)


#
# Return the minimum Tweet ID or None if there are no tweets.
#
def get_min_tweet_id(session, username):

	retval = None
	row = session.query(func.min(Tweets.tweet_id).label("min")).filter(
		Tweets.username == username).first()

	if row:
		retval = row.min

	return(retval)


#
# Prime our Tweets table by fetching the first one.
#
def getTweetsPrime(config, twitter, tweets_left):

	logger.info("No Max ID, which means no tweets, fetch one to prime our table.")
	tweets = getTweets(twitter, config.get("twitter_username"), 1)

	if len(tweets["tweets"]) == 0:
		logger.warning("No tweets found, completely bailing out!")
		return(None)
		
	write_tweets(tweets["tweets"])

	min_id = tweets["tweets"][0]["id"]
	max_id = tweets["tweets"][0]["id"]
	logger.info("min_tweet_id={} max_tweet_id={}".format(min_id, max_id))

	tweets_left -= 1

	return(tweets_left, len(tweets["tweets"]), min_id, max_id)


#
# Fetch tweets that are before the lowest Tweet ID we currently have available.
#
def getTweetsPast(config, twitter, tweets_left, min_id):

	num_tweets_fetched = 0

	num_passes_zero_tweets = 3
	num_passes_zero_tweets_left = num_passes_zero_tweets

	while True:

		tweets_to_fetch = 200
		#tweets_to_fetch = 1 # Debugging
		if tweets_left < tweets_to_fetch:
			tweets_to_fetch = tweets_left

		tweets = getTweets(twitter, config.get("twitter_username"), 
			tweets_to_fetch, max_id = min_id)
		tweets_left -= len(tweets["tweets"])
		write_tweets(tweets["tweets"])
		num_tweets_fetched += len(tweets["tweets"])

		logger.info("tweets_fetched={}, tweets_left={}".format(len(tweets["tweets"]), tweets_left))
		if tweets_left <= 0:
			logger.info("Tweets left is {}, done fetching past tweets!".format(tweets_left))
			break

		if len(tweets["tweets"]) == 0:

			num_passes_zero_tweets_left -= 1
			logger.info("We got zero tweets this pass! passes_left={}".format(
				num_passes_zero_tweets_left))

			if num_passes_zero_tweets_left <= 0:
				logger.info("Number of zero passes left == 0. Yep, we're at the end.")
				break

			continue

		#
		# We got some tweets, reset our zero tweets counter
		#
		num_passes_zero_tweets_left = num_passes_zero_tweets

		#
		# Get the ID of the last tweet as our new min_id
		#	
		min_id = tweets["tweets"][len(tweets["tweets"]) - 1]["id"]
		logger.info("New min_id is {}".format(min_id))

	return(tweets_left, num_tweets_fetched, min_id)


#
# Fetch tweets made after the latest one in our table.
#
def getTweetsFuture(config, twitter, tweets_left, max_id):

	num_tweets_fetched = 0

	num_passes_zero_tweets = 3
	num_passes_zero_tweets_left = num_passes_zero_tweets

	while True:

		tweets_to_fetch = 200
		#tweets_to_fetch = 1 # Debugging
		if tweets_left < tweets_to_fetch:
			tweets_to_fetch = tweets_left

		tweets = getTweets(twitter, config.get("twitter_username"), tweets_to_fetch, min_id = max_id)
		tweets_left -= len(tweets["tweets"])
		write_tweets(tweets["tweets"])
		num_tweets_fetched += len(tweets["tweets"])

		logger.info("tweets_fetched={}, tweets_left={}".format(len(tweets["tweets"]), tweets_left))
		if tweets_left <= 0:
			logger.info("Tweets left is {}, done fetching past tweets!".format(tweets_left))
			break

		if len(tweets["tweets"]) == 0:

			num_passes_zero_tweets_left -= 1
			logger.info("We got zero tweets this pass! passes_left={}".format(
				num_passes_zero_tweets_left))

			if num_passes_zero_tweets_left <= 0:
				logger.info("Number of zero passes left == 0. Yep, we're at the end.")
				break

			continue

		#
		# We got some tweets, reset our zero tweets counter
		#
		num_passes_zero_tweets_left = num_passes_zero_tweets

		#
		# Get the ID of the first tweet as our new max_id
		#	
		max_id = tweets["tweets"][0]["id"]
		logger.info("New max_id is {}".format(max_id))

	return(tweets_left, num_tweets_fetched)


#
# Our main function.
#
def main(args):

	ini_file = os.path.dirname(os.path.realpath(__file__)) + "/../config.ini"
	logger.info("Ini file path: {}".format(ini_file))
	config = configParser.Config(ini_file)

	twitter = verify_twitter_credentials(config)

	max_id = get_max_tweet_id(session, config.get("twitter_username"))
	min_id = get_min_tweet_id(session, config.get("twitter_username"))
	logger.info("min_tweet_id={} max_tweet_id={}".format(min_id, max_id))

	tweets_left = args.num
	num_tweets_fetched_total = 0

	if not max_id:
		#
		# We have no tweets, so fetch one.
		#
		(tweets_left, num_tweets_fetched, min_id, max_id) = getTweetsPrime(
			config, twitter, tweets_left)
		num_tweets_fetched_total += num_tweets_fetched


	#
	# Now fetch tweets before our min Tweet ID.
	#
	(tweets_left, num_tweets_fetched, min_id) = getTweetsPast(
		config, twitter, tweets_left, min_id)
	num_tweets_fetched_total += num_tweets_fetched

	if tweets_left <= 0:
		logger.info("We're done fetching tweets ({} tweets left)".format(tweets_left))
		return(None)

	max_id = get_max_tweet_id(session, config.get("twitter_username"))


	#
	# Now fetch tweets after our max tweet ID in case some new ones came in.
	#
	(tweets_left, num_tweets_fetched) = getTweetsFuture(
		config, twitter, tweets_left, max_id)
	num_tweets_fetched_total += num_tweets_fetched

	logger.info("Total Number of tweets fetched: {}".format(num_tweets_fetched_total))

	logger.info("Now backfilling reply info on any tweets that are replies.")
	num_tweets_backfilled = backfill_tweets(twitter)
	logger.info("total_tweets_backfilled=%d" % num_tweets_backfilled)

	logger.info("ok=1")

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



