#!/usr/bin/env python3
# :set softtabstop=8 noexpandtab
#
# Get our Twitter credentials and store them in an ini file
#


import argparse
import configparser
import datetime
import json
import logging as logger
import logging.config
import os
import sys
import time
import webbrowser

import twython


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


	retval["twitter_app_key"] = get_input(config, "twitter_app_key", 
		"Enter your Consumer API Key here")
	retval["twitter_app_secret"] = get_input(config, "twitter_app_secret", 
		"Enter your Consumer API Secret Key here")

	retval["twitter_username"] = get_input(config, "twitter_username", 
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

	retval["created"] = int(time.time())

	return(retval)


#
# Read our configuration from the ini file and return a parsed config object.
#
def get_config(ini_file):

	# Touch our file
	open(ini_file, "a").close()
	
	config = configparser.ConfigParser()
	config.read(ini_file)

	if not config.has_section("settings"):
		config.add_section("settings")

	return(config)


#
# Write our configuration to disk.
#
def write_config(config, ini_file):

	with open(ini_file, "w") as file:
		config.write(file)


#
# Prompt the user to enter input for a value in our settings
#
# config - ConfigParser object
# key - Key to read from "settings" stanza.
# input_string - Base input string to show the user (default may be filled in)
#
def get_input(config, key, input_string):

	default = ""
	if config.has_option("settings", key):
		default = config.get("settings", key)

	if default:
		input_string += " [{}]: ".format(default)
	else:
		input_string += ": "

	value = input(input_string)

	#
	# If the user hit enter, use the default value!
	#
	if not value:
		if default:
			value = default
		else:
			raise Exception("You must enter a value!")

	return(value)


#
# Our main function.
#
def main(args):

	ini_file = os.path.dirname(os.path.realpath(__file__)) + "/../config.ini"
	logger.info("Ini file path: {}".format(ini_file))

	config = get_config(ini_file)

	twitter_data = getTwitterAuthData(config)

	for key in twitter_data:
		config.set("settings", key, str(twitter_data[key]))

	write_config(config, ini_file)


	#
	# Verify our Twitter credentials
	#
	twitter = twython.Twython(twitter_data["twitter_app_key"], 
		twitter_data["twitter_app_secret"], 
		twitter_data["final_oauth_token"], 
		twitter_data["final_oauth_token_secret"])

	creds = twitter.verify_credentials()
	rate_limit = twitter.get_lastfunction_header('x-rate-limit-remaining')
	logger.info("Rate limit left for verifying credentials: " + rate_limit)

	#
	# Who am I, again?
	#
	screen_name = creds["screen_name"]
	logger.info("My screen name is: " + screen_name)


main(args)


