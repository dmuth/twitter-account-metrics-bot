
# Twitter Account Metrics Bot

An app to get metrics from Twitter accounts and report them to Telegram via a bot.

<img src="./img/statistics.png" width="150" align="right" />

This is useful for monitoring activity on organization social media accounts.


## Requirements

- Docker
- Go to <a href="https://developer.twitter.com/">https://developer.twitter.com/</a> and create an App.  Note your Consumer API Key and Secret Key.


## Screenshots

<a href="./img/askamex-tweets-7-days.png"><img src="./img/askamex-tweets-7-days.png" alt="AskAmex Tweets for 7 days" width="250"/></a> <a href="./img/askamex-tweets-3-days.png"><img src="./img/askamex-tweets-3-days.png" alt="AskAmex Tweets for 3 days" width="250"/></a> <a href="./img/askamex-tweets-6-hours.png"><img src="./img/askamex-tweets-6-hours.png" alt="AskAmex Tweets for 6 hours" width="250"/></a>


## Setup

- Clone this repo to your machine
- Run `./bin/run.sh 0-get-credentials` to configure the app.  You'll need your Twiter API data, and (optionally) AWS and Telegram credentials as well.
   - AWS credentials can be obtained from the AWS console and is beyond the scope of this document.
   - Telegram credentials can be obtained from <a href="https://telegram.me/BotFather">messaging BotFather</a> and following the instructions.
- Manual usage:
   - Run `./bin/run.sh 1-fetch-tweets` to fetch tweets and store them to `tweets.db`, which is a SQLite database.
   - Run `./bin/run.sh 1-export-to-json` to export all tweets to `tweets.json`.
   - Run `./bin/run.sh 2-telegram-bot` to start reporting tweet stats to Telegram
   - Run `./bin/run.sh 2-backup-tweets` to start a script that periodically backs up the `tweets.db` file to AWS S3.
- Normal usage:
   - Run `docker-compose up -d` and tweets will start being downloaded with stats being written to the Telegram Channel of your user.  


## Development

- To work on a script interactively:
   - `./bin/dev.sh` - This will launch the container with an interactive shell.
   - Scripts live in `/mnt/bin/` on this container.
- To download the latest backup: `./bin/aws/download-latest-backup`


# FAQ

## How do I get Telegram Group/Chat IDs?

From <a href="https://stackoverflow.com/a/45577773/196073">https://stackoverflow.com/a/45577773/196073</a>:
- Go to your group in <a href="https://web.telegram.org/">the web interface</a> and grab the link. e.g. https://web.telegram.org/#/im?p=g154513121
- Copy That number after g and put a (-) Before That. e.g. -154513121
- Send Your Message to group. e.g. `bot.send_message(-154513121, "Hi")`


# Credits

- <a href="https://twython.readthedocs.io/en/latest/">Twython</a> - The Twitter client for Python, this made using Twitter's API a breeze.
- <a href="https://www.sqlite.org/index.html">SQLite</a> - Used for data storage.
- <a href="https://www.sqlalchemy.org/">SQLAlchemy</a> - This is my first project with SQLAlchemy, and it made tasks such as database schema maintenance and interacting with the database way easier to do!
- <a href="https://github.com/python-telegram-bot/python-telegram-bot">python-telegram-bot</a> - I use this module for connecting to Telegram, and it too makes my life much easier.
- Icons made by <a href="https://www.freepik.com/" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a> is licensed by <a href="http://creativecommons.org/licenses/by/3.0/"  title="Creative Commons BY 3.0" target="_blank">CC 3.0 BY</a>

# Author

Myself, Douglas Muth.  Ways you can get in touch with me:
- <a href="http://www.dmuth.org/">My website</a>
- <a href="http://twitter.com/dmuth">Twitter</a>
- <a href="http://facebook.com/dmuth">Facebook</a>
- ...or just file a bug on this repo!



