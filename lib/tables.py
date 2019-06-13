

from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Text
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

