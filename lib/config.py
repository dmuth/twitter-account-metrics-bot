

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


