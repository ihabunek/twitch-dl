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

# Upload the file to S3, then delete the local copy
set -e
aws s3 cp "${FILE}" "s3://$BUCKET/" --storage-class GLACIER
rm -f "${FILE}"

exit 0