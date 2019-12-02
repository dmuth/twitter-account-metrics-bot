#!/bin/bash
#
# Back up our database to S3.
#

# Errors are fatal
set -e

NUM_TO_KEEP=20
LOOP_SECONDS=900

if test ! "$1"
then
	echo "! "
	echo "! Syntax: $0 s3_bucket [ num_backups_to_keep ] [ seconds_to_wait_between_loops ]"
	echo "! "
	exit 1
fi

S3=$1

if test "$2"
then
	NUM_TO_KEEP=$2
fi

if test "$3"
then
	LOOP_SECONDS=$3
fi


export AWS_ACCESS_KEY_ID=$(cat /mnt/config.ini | grep aws_access_key_id | cut -d= -f2 | awk '{print $1}')
export AWS_SECRET_ACCESS_KEY=$(cat /mnt/config.ini | grep aws_secret_access_key | cut -d= -f2 | awk '{print $1}')

if test ! "$AWS_ACCESS_KEY_ID"
then
	echo "! "
	echo "! Unable to load AWS_ACCESS_KEY_ID. Please check your config.ini file."
	echo "! "
	exit 1
fi

if test ! "$AWS_SECRET_ACCESS_KEY"
then
	echo "! "
	echo "! Unable to load AWS_SECRET_ACCESS_KEY. Please check your config.ini file."
	echo "! "
	exit 1
fi


echo "# "
echo "# Starting Tweet backup script"
echo "# "
echo "# Backing up to S3 location: ${S3}"
echo "# Keeping this many backups: ${NUM_TO_KEEP}"
echo "# Looping this many seconds: ${LOOP_SECONDS}"
echo "# "

while true
do

	FILE=$(date +%Y%m%d-%H%M%S)
	TARGET="${S3}tweets-${FILE}.db"

	TMP=$(mktemp /tmp/backup-XXXXXXX)

	echo "# Making a copy of the database..."
	cp /mnt/tweets.db $TMP

	echo "# Now backing up database to '$TARGET' on S3..."
	aws s3 cp $TMP $TARGET

	#
	# Remove our temp file
	#
	rm -fv $TMP

	#
	# Delete all but the most recent backups
	# (Hopefully there is versioning turned on in S3 just in case an older backup needs to be retrieved)
	#
	COUNT_DELETED=0
	LINES_TO_KEEP=$(( $NUM_TO_KEEP + 1 ))

	for FILE in $(aws s3 ls $S3 | sort -r | sed -n $LINES_TO_KEEP,\$p | awk '{ print $4 }' )
	do
		DELETE="${S3}${FILE}"
		aws s3 rm ${DELETE}
		COUNT_DELETED=$(( $COUNT_DELETED + 1 ))

	done

	#
	# Put this output in a date format that Splunk will recognize
	#
	echo "$(date "+%Y-%m-%d %H:%M:%S"),$(date +%s%N | cut -b14-16) ok=1 num_to_keep=${NUM_TO_KEEP} old_backups_deleted=${COUNT_DELETED}"

	echo "# Current contents of S3 bucket ${S3} "
	aws s3 ls $S3

	echo "Sleeping for ${LOOP_SECONDS} seconds..."
	sleep ${LOOP_SECONDS}

done


