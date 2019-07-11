#!/usr/bin/env python3
# Vim: :set softtabstop=0 noexpandtab tabstop=4
#
# Dump our tweets as JSON-formatted data
#

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
from tables import create_all, get_session, Tweets

logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s')

#
# Open our file for output
#
output = "/mnt/tweets.json"
logger.info("Writing to file '{}'...".format(output))
f = open(output, "w")

#
# Connect to the database
#
session = get_session()

#
# Grab all Tweets and export them
#
rows = session.query(Tweets).all()
for row in rows:
	print(row.json()) # Debugging
	f.write(row.json() + "\n")

cnt = session.query(Tweets).count()
logger.info("Wrote {} rows as JSON".format(cnt))

f.close()

logger.info("Done!")


