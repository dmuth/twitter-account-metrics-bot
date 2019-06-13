#!/usr/bin/env python3
# :set softtabstop=8 noexpandtab
#
# Get our Twitter credentials
#


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
from tables import create_all, get_session, Config 

#
# Parse our arguments
#
parser = argparse.ArgumentParser(description = "Get app credentials from Twitter")
parser.add_argument("--debug", action = "store_true")
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
# Prompt the user for input and upsert into the data, showing 
# the default value if it's already in the database.
#
# session - The database session
# name - The name of the field from the table
# input_string - Base input string to show the user (default may be filled in)
#
# Returns the value that the user entered
#
def get_input(session, name, input_string):

	#
	# See if the row exists
	#
	row = session.query(Config).filter(Config.name == name).first()

	if row:
		input_string += " [{}]: ".format(row.value)
	else:
		input_string += ": "

	value = input(input_string)

	#
	# If the user hit enter, use the default value!
	#
	if not value:
		if row:
			value = row.value
		else:
			raise Exception("You must enter a value!")

	#
	# Save what we did
	#
	if not row:
		row = Config(name = name, value = value)
	else:
		row.value = value

	session.add(row)
	session.commit()

	return(value)



#
# Fetch our data from the database.  If we don't have any data, then
# go through the process of getting auth tokens, which is a somewhat involved
# process which also includes opening up a web browser window. (ugh)
#
# @return dict A dictionary with our credentials
# @return object A SQLite object representing the row
#
def getTwitterAuthData():

	retval = {}

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


	retval["app_key"] = get_input(session, "twitter_app_key", 
		"Enter your Consumer API Key here")
	retval["app_secret"] = get_input(session, "twitter_app_secret", 
		"Enter your Consumer API Secret Key here")

	retval["twitter_username"] = get_input(session, "twitter_username", 
		"Username you want to get Tweet stats on")

	twitter = twython.Twython(retval["app_key"], retval["app_secret"])
	auth = twitter.get_authentication_tokens()

	auth_url = auth["auth_url"]
	logger.info("Auth URL: " + auth_url)

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

	oauth_verifier = input("Enter Your PIN: ")

	oauth_token = auth['oauth_token']
	oauth_token_secret = auth['oauth_token_secret']
	logger.info("OAUTH Token: " + oauth_token)
	logger.info("OAUTH Token Secret: " + oauth_token_secret)

	twitter = twython.Twython(retval["app_key"], retval["app_secret"], 
		oauth_token, oauth_token_secret)

	try:
		final_step = twitter.get_authorized_tokens(oauth_verifier)

	except twython.exceptions.TwythonError as e:
		print ("! ")
		print ("! Caught twython.exceptions.TwythonError:", e)
		print ("! ")
		print ("! Did you enter the right PIN code?")
		print ("! ")
		sys.exit(1)

	retval["final_oauth_token"] = final_step['oauth_token']
	retval["final_oauth_token_secret"] = final_step['oauth_token_secret']

	#
	# Remove and save our final oauth tokens
	#
	session.query(Config).filter(Config.name == "twitter_final_oauth_token").delete()
	session.query(Config).filter(Config.name == "twitter_final_oauth_token_secret").delete()
	row = Config(name = "twitter_final_oauth_token", value = retval["final_oauth_token"])
	session.add(row)
	row = Config(name = "twitter_final_oauth_token_secret", value = 
		retval["final_oauth_token_secret"])
	session.add(row)
	session.commit()

	logger.info("Final OUATH token: " + retval["final_oauth_token"])
	logger.info("Final OAUTH token secret: " + retval["final_oauth_token_secret"])

	retval["created"] = int(time.time())

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

	#
	# Who am I, again?
	#
	screen_name = creds["screen_name"]
	logger.info("My screen name is: " + screen_name)


main(args)


