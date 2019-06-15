#!/bin/bash
#
# Back up our database to S3.
#

# Errors are fatal
set -e

LOOP_SECONDS=${LOOP_SECONDS:=900}
NUM_TO_KEEP=${NUM_TO_KEEP:=20}


if test ! "$S3"
then
	echo "! "
	echo "! Environment variable \"S3\" needs to be set with the S3 bucket to backup to!"
	echo "! "
	exit 1
fi


#
# Check for and copy in our AWS credentials from the host container.
#
AWS_CREDS=/mnt/aws-credentials.txt
if test ! -f $AWS_CREDS
then
	echo "! "
	echo "! AWS Credentials not found in $AWS_CREDS!  Stopping."
	echo "! "
	exit 1
fi

cp $AWS_CREDS $HOME/.aws/credentials

AWS_CREDS=$HOME/.aws/credentials
if test ! -f $AWS_CREDS
then
	echo "! "
	echo "! AWS Credentials not found in $AWS_CREDS!  Stopping."
	echo "! "
	exit 1
fi



echo "# "
echo "# Starting Tweet backup script"
echo "# "
echo "# Backing up to S3 location: ${S3}"
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

	echo "Sleeping for ${LOOP_SECONDS} seconds..."
	sleep ${LOOP_SECONDS}

done


