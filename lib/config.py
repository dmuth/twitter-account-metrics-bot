

import configparser

#
# This class is used for parsing our configuration file and updating it.
#
class Config:

	#
	# Our ini file.
	#
	ini_file = ""

	#
	# Our config object
	#
	config = None


	#
	# Our and parse our config file.
	#
	def __init__(self, ini_file):
		self.ini_file = ini_file

		# Touch our file
		open(self.ini_file, "a").close()

		self.config = configparser.ConfigParser()
		self.config.read(self.ini_file)

		if not self.config.has_section("settings"):
			self.config.add_section("settings")


	#
	# Write our configuration to disk.
	#
	def write_config(self):

		with open(self.ini_file, "w") as file:
			self.config.write(file)


	#
	# Prompt the user to enter input for a value in our settings
	#
	# key - Key to read from "settings" stanza.
	# input_string - Base input string to show the user (default may be filled in)
	#
	def get_input(self, key, input_string):

		default = ""
		if self.config.has_option("settings", key):
			default = self.config.get("settings", key)

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

		self.config.set("settings", key, str(value))

		return(value)


	#
	# Return the value of a specific key.
	#
	def get(self, key):
		return(self.config.get("settings", key))


	#
	# Return all items with their values in a section as a dictionary.
	#
	def get_items(self):

		retval = {}

		for k, v in self.config.items("settings"):
			retval[k] = v

		return(retval)


	#
	# Prompt a user to enter an input string, with a default value if they just hit enter
	#
	def input_default(self, string, default):

		retval = input(string + " ")
		if not retval:
			retval = default

		return(retval)


	#
	# This function prints the user for input using input_default, and will check the
	# result to see if the user entered "y" or not.  
	#
	# A boolean is retuned.  True for "y", otherwise FAlse.
	#
	def input_default_yes(self, string):

		choice = self.input_default(string + " [Y/n]", "y")

		if choice[0] == "Y" or choice[0] =="y":
			return(True)

		return(False)




