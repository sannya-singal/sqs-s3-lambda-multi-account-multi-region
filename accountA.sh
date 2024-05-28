export AWS_ACCESS_KEY_ID=111111111111
export AWS_SECRET_ACCESS_KEY=test


ACCOUNT_ID=$(awslocal sts get-caller-identity --query Account --output text)
echo "> Current Account ID: $ACCOUNT_ID"


QUEUE_NAME="team-queue-${ACCOUNT_ID}"
BUCKET_NAME="team-bucket-${ACCOUNT_ID}"

echo "> Creating Queue: $QUEUE_NAME..."
QUEUE_URL=$(awslocal sqs create-queue --queue-name $QUEUE_NAME --attributes VisibilityTimeout=300 --query 'QueueUrl' --output text)
echo "Queue created URL: $QUEUE_URL"

echo "> Setting Queue Policy for $QUEUE_URL..."
awslocal sqs set-queue-attributes --queue-url $QUEUE_URL --attributes file://sqs-policy1.json

echo "> Creating Bucket: $BUCKET_NAME..."
awslocal s3api create-bucket --bucket $BUCKET_NAME
echo "Bucket created: $BUCKET_NAME"

echo "> Setting Bucket Policy for $BUCKET_NAME..."
awslocal s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://s3-policy1.json

echo "Setup completed for Account ID: $ACCOUNT_ID"