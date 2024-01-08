#!/bin/bash

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null
then
    echo "AWS CLI not installed. Please install and configure it."
    exit 2
fi

# Check for correct number of arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <s3-bucket-name> <file-name>"
    exit 2
fi

BUCKET=$1
FILE=$2

# Check if file exists in the S3 bucket
if aws s3 ls "s3://$BUCKET/$FILE" > /dev/null; then
    echo "File $FILE exists in bucket $BUCKET."
    exit 1
else
    echo "File $FILE does not exist in bucket $BUCKET."
    exit 0
fi
