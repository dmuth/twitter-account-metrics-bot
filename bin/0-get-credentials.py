#!/usr/bin/env python3
# :set softtabstop=8 noexpandtab
#
# Get our Twitter credentials and store them in an ini file
#


import argparse
import datetime
import json
import logging as logger
import logging.config
import os
import sys
import time
import webbrowser

import twython


sys.path.append("lib")
import config as configParser

#
# Parse our arguments
#
parser = argparse.ArgumentParser(description = "Get Twitter app credentials and store them in an INI file")
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
# Prompt the user to enter Twitter data, using what we have for defaults.
#
# @return dict A dictionary with our credentials
#
def getTwitterAuthData(config):

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


	retval["twitter_app_key"] = config.get_input("twitter_app_key", 
		"Enter your Consumer API Key here")
	retval["twitter_app_secret"] = config.get_input("twitter_app_secret", 
		"Enter your Consumer API Secret Key here")

	retval["twitter_username"] = config.get_input("twitter_username", 
		"Username you want to get Tweet stats on")

	twitter = twython.Twython(retval["twitter_app_key"], retval["twitter_app_secret"])
	auth = twitter.get_authentication_tokens()

	auth_url = auth["auth_url"]
	logger.info("Auth URL: " + auth_url)

	print("# ")
	print("# For the next step, you need to an authentication page on Twitter,")
	print("# which will display a PIN.  Please enter that PIN below!")
	print("# ")
	print("# ")
	print("# ")
	print("# Please open this URL in your browser, click \"Authorize\", and get your PIN:")
	print("# ")
	print("# {}".format(auth_url))
	print("# ")

	oauth_verifier = input("Enter Your PIN: ")

	oauth_token = auth['oauth_token']
	oauth_token_secret = auth['oauth_token_secret']
	logger.info("OAUTH Token: " + oauth_token)
	logger.info("OAUTH Token Secret: " + oauth_token_secret)

	twitter = twython.Twython(retval["twitter_app_key"], retval["twitter_app_secret"], 
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

	logger.info("Final OUATH token: " + retval["final_oauth_token"])
	logger.info("Final OAUTH token secret: " + retval["final_oauth_token_secret"])

	retval["twitter_created"] = int(time.time())

	return(retval)


#
# Optionally configure and verify Twitter credentials
#
def configureTwitter(config):

	verify = False
	choice = config.input_default_yes("Configure Twitter app?")

	if choice:
		twitter_data = getTwitterAuthData(config)
		config.write_config()
		verify = True

	if not verify:
		verify = config.input_default_yes("Verify Twitter credentials?")

	if not verify:
		return

	#
	# Verify our Twitter credentials
	#
	logger.info("Verifying Twitter credentials...")
	twitter = twython.Twython(config.get("twitter_app_key"), 
		config.get("twitter_app_secret"), 
		config.get("final_oauth_token"), 
		config.get("final_oauth_token_secret"))

	creds = twitter.verify_credentials()
	rate_limit = twitter.get_lastfunction_header('x-rate-limit-remaining')
	logger.info("Rate limit left for verifying credentials: " + rate_limit)

	#
	# Who am I, again?
	#
	screen_name = creds["screen_name"]
	logger.info("My screen name is: " + screen_name)


#
# Our main function.
#
def main(args):

	ini_file = os.path.dirname(os.path.realpath(__file__)) + "/../config.ini"
	logger.info("Ini file path: {}".format(ini_file))

	config = configParser.Config(ini_file)

	configureTwitter(config)


main(args)


