#!/usr/bin/env python3
# :set softtabstop=8 noexpandtab


import argparse
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


#
# SQLAlchemy stuff which will eventually be put into an ORM class in a separate file
#
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Text

db = create_engine("sqlite:///tweets.db")

metadata = MetaData()
users = Table("config", metadata,
	Column("name", Text, primary_key=True),
	Column("value", Text)
	)

metadata.create_all(db)
conn = db.connect()


#
# Set up the logger
#
logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s')


#
# Parse our arguments
#
parser = argparse.ArgumentParser(description = "Get app credentials from Twitter")
args = parser.parse_args()


#
# Fetch our data from the database.  If we don't have any data, then
# go through the process of getting auth tokens, which is a somewhat involved
# process which also includes opening up a web browser window. (ugh)
#
# @return dict A dictionary with our credentials
# @return object A SQLite object representing the row
#
def getTwitterAuthData():

	print("# ")

	print("# ")
	print("# First things first!  You'll need to go to Twitter's Apps page, ")
	print("# create an app, then click on the 'Keys and Tokens' tab to get")
	print("# your API Key and Secret.")
	print("# ")

	url = "https://developer.twitter.com/en/apps"
	print("# ")
	print("# Please open this URL in your browser: {}".format(url))
	print("# ")
	print("# ")
	print("# ")

	app_key = input("Enter your Consumer API Key here: ")
	app_secret = input("Enter your Consumer API Secret Key here: ")

	twitter = twython.Twython(app_key, app_secret)
	auth = twitter.get_authentication_tokens()

	auth_url = auth["auth_url"]
	logger.debug("Auth URL: " + auth_url)

	print("# ")
	print("# For the next step, you need to an authentication page on Twitter,")
	print("# which will display a PIN.  Please enter that PIN below!")
	print("# ")
	print("# ")
	print("# ")
	print("# Please open this URL to get your PIN:")
	print("# ")
	print("# {}".format(auth_url))
	print("# ")

	#webbrowser.open(auth_url)
	oauth_verifier = input("Enter Your PIN: ")

	oauth_token = auth['oauth_token']
	oauth_token_secret = auth['oauth_token_secret']
	logger.debug("OAUTH Token: " + oauth_token)
	logger.debug("OAUTH Token Secret: " + oauth_token_secret)

	twitter = twython.Twython(app_key, app_secret, oauth_token, oauth_token_secret)

	try:
		final_step = twitter.get_authorized_tokens(oauth_verifier)

	except twython.exceptions.TwythonError as e:
		print ("! ")
		print ("! Caught twython.exceptions.TwythonError:", e)
		print ("! ")
		print ("! Did you enter the right PIN code?")
		print ("! ")
		sys.exit(1)

	final_oauth_token = final_step['oauth_token']
	final_oauth_token_secret = final_step['oauth_token_secret']
	logger.debug("Final OUATH token: " + final_oauth_token)
	logger.debug("Final OAUTH token secret: " + final_oauth_token_secret)

	retval = {
		"app_key": app_key,
		"app_secret": app_secret,
		"final_oauth_token": final_oauth_token,
		"final_oauth_token_secret": final_oauth_token_secret,
		"created": int(time.time()),
		}

	return(retval)


#
# Our main function.
#
def main(args):

	#
	# Create our data object for writing to the data table.
	#
	twitter_data = getTwitterAuthData()


	#
	# Verify our Twitter credentials
	#
	twitter = twython.Twython(twitter_data["app_key"], twitter_data["app_secret"], 
		twitter_data["final_oauth_token"], twitter_data["final_oauth_token_secret"])

	creds = twitter.verify_credentials()
	rate_limit = twitter.get_lastfunction_header('x-rate-limit-remaining')
	logger.info("Rate limit left for verifying credentials: " + rate_limit)

	query = "INSERT INTO config (name, value) VALUES (:name, :value) ON CONFLICT(name) DO UPDATE SET value = :value"
	conn.execute(query, name = "app_key", value = twitter_data["app_key"])
	conn.execute(query, name = "app_secret", value = twitter_data["app_secret"])
	conn.execute(query, name = "final_oauth_token", value = twitter_data["final_oauth_token"])
	conn.execute(query, name = "final_oauth_token_secret", value = twitter_data["final_oauth_token_secret"])

	logger.info("Write Twitter credentials to database!")

	#
	# Who am I, again?
	#
	screen_name = creds["screen_name"]
	logger.info("My screen name is: " + screen_name)


main(args)


