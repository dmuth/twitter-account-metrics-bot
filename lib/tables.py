

import json

from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Text, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


#
# Our Config table
#
class Config(Base):

	__tablename__ = "config"

	name = Column(String, primary_key = True)
	value = Column(String)

	def __repr__(self):
		return "<Config(name='{}', value='{}')>".format(
			self.name, self.value)

class Tweets(Base):
	__tablename__ = "tweets"
	
	id = Column(Integer, primary_key = True)
	tweet_id = Column(Integer)
	reply_age = Column(Integer)
	time_t = Column(Integer)
	date = Column(DateTime)
	username = Column(Text)
	text = Column(Text)
	url = Column(Text)
	reply_tweet_id = Column(Integer)
	reply_error = Column(Text)
	reply_username = Column(Text)
	reply_time_t = Column(Integer)
	reply_url = Column(Text)


	def __repr__(self):
		return "<Tweets(id='{}', tweet_id='{}')>".format(
			self.id, self.tweet_id)


	#
	# Return the current row as JSON formated.
	#
	def json(self):

		retval = {
			"date": str(self.date),
			"tweet_id": self.tweet_id,
			"reply_age": self.reply_age,
			"time_t": self.time_t,
			"username": self.username,
			"text": self.text,
			"url": self.url,
			"reply_tweet_id": self.reply_tweet_id,
			"reply_error": self.reply_error,
			"reply_username": self.reply_username,
			"reply_time_t": self.reply_time_t,
			"reply_url": self.reply_url
			}

		return(json.dumps(retval))


#
# Create our schema
#
def create_all(db):
	Base.metadata.create_all(db)


#
# Connect to the database and return a session
#
def get_session():

	db = create_engine("sqlite:///tweets.db", echo = False)
	Session = sessionmaker(bind = db, autocommit = False)
	session = Session()
	create_all(db)
	return(session)

