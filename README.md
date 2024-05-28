# Testing cross-account and cross-region SQS S3 Lambda setup

This repository contains an example on how to deploy a multi-account, multi-region setup in which a Lambda function in one account invoked by a REST API sends a message to an SQS queue in another account and another region and uploads a file to an S3 bucket in the same account and region as the SQS queue.

LocalStack supports cross-account setup that allows you to namespace resources based on the AWS Account ID. In this example, you can use three local AWS accounts to simulate the cross-account setup. They are:

- **Account A** (`111111111111`): The account that contains the SQS queue and the S3 bucket in `us-east-1` region.
- **Account B** (`222222222222`): The account that contains the SQS queue and the S3 bucket in `eu-west-1` region.
- **Account C** (`333333333333`): The account that contains the Lambda function and the API Gateway in `us-east-1` region.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [LocalStack](https://docs.localstack.cloud/getting-started/installation/)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) & [`awslocal`](https://github.com/localstack/awscli-local)

Start LocalStack with the following command:

```bash
DEBUG=1 ENFORCE_IAM=1 localstack start
```

You can follow the instructions below or run the whole sample using the provided three scripts.

```bash
./accountA.sh
./accountB.sh
./accountC.sh
```

## Create the SQS queue and S3 bucket in Account A

For Account A we will open a terminal and provide the following `AWS_ACCOUNT_ID` and `AWS_SECRET_ACCESS_KEY` environment variables:

```bash
export AWS_ACCESS_KEY_ID=111111111111
export AWS_SECRET_ACCESS_KEY=test
```

Run the following commands to store the account ID, queue name and bucket name in variables:

```bash
ACCOUNT_ID=$(awslocal sts get-caller-identity --query Account --output text)
QUEUE_NAME="team-queue-${ACCOUNT_ID}"
BUCKET_NAME="team-bucket-${ACCOUNT_ID}"
```

Create the SQS queue in Account A and set the policy to allow Account C to send messages to the queue in Account A:

```bash
QUEUE_URL=$(awslocal sqs create-queue --queue-name $QUEUE_NAME --attributes VisibilityTimeout=300 --query 'QueueUrl' --output text)
awslocal sqs set-queue-attributes --queue-url $QUEUE_URL --attributes file://sqs-policy1.json
```

Create the S3 bucket in Account A and set the policy to allow Account C to upload files to the bucket in Account A:

```bash
awslocal s3api create-bucket --bucket $BUCKET_NAME
awslocal s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://s3-policy1.json
```

## Create the SQS queue and S3 bucket in Account B

For Account B we will open another terminal and provide the following `AWS_ACCOUNT_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_REGION=eu-west-1` environment variables:

```bash
export AWS_ACCESS_KEY_ID=222222222222
export AWS_REGION=eu-west-1
export AWS_SECRET_ACCESS_KEY=test
```

Run the following commands to store the account ID, queue name and bucket name in variables:

```bash
ACCOUNT_ID=$(awslocal sts get-caller-identity --query Account --output text)
QUEUE_NAME="team-queue-${ACCOUNT_ID}"
BUCKET_NAME="team-bucket-${ACCOUNT_ID}"
```

Create the SQS queue in Account B and set the policy to allow Account C to send messages to the queue in Account B:

```bash
QUEUE_URL=$(awslocal sqs create-queue --queue-name $QUEUE_NAME --region eu-west-1 --attributes VisibilityTimeout=300 --query 'QueueUrl' --output text)
awslocal sqs set-queue-attributes --queue-url $QUEUE_URL --attributes file://sqs-policy2.json
```

Create the S3 bucket in Account B and set the policy to allow Account C to upload files to the bucket in Account B:

```bash
awslocal s3api create-bucket --bucket $BUCKET_NAME
awslocal s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://s3-policy2.json
```

## Create the Lambda function and API Gateway in Account C

For Account C we will open another terminal and provide the following `AWS_ACCOUNT_ID` and `AWS_SECRET_ACCESS_KEY` environment variables:

```bash
export AWS_ACCESS_KEY_ID=333333333333
export AWS_SECRET_ACCESS_KEY=test
```

Create lambda execution role and attach it to the policy:

```bash
awslocal iam create-role --role-name common-lambda-role --assume-role-policy-document file://trust-policy.json
awslocal iam put-role-policy --role-name common-lambda-role --policy-name common-lambda-policy --policy-document file://lambda-policy.json
```

Create the deployment package for the Lambda function and create the function:

```bash
zip lambda_function.zip lambda_function.py
awslocal lambda create-function --function-name CommonLambda \
                --runtime python3.11 \
                --role arn:aws:iam::333333333333:role/common-lambda-role \
                --handler lambda_function.handler \
                --zip-file fileb://lambda_function.zip \
                --timeout 300
```

Create the API Gateway and store the API ID and the resource ID in variables:

```bash
awslocal apigateway create-rest-api --name "CommonLambdaApi"
API_ID=$(awslocal apigateway get-rest-apis --query 'items[?name==`CommonLambdaApi`].id' --output text)
RESOURCE_ID=$(awslocal apigateway get-resources --rest-api-id $API_ID --query 'items[?path==`/`].id' --output text)
```

Create a resource and a POST method for the API Gateway:

```bash
UPLOAD_RESOURCE_ID=$(awslocal apigateway create-resource --rest-api-id $API_ID --parent-id $RESOURCE_ID --path-part upload --query 'id' --output text)
awslocal apigateway put-method --rest-api-id $API_ID --resource-id $UPLOAD_RESOURCE_ID --http-method POST --authorization-type "NONE"
```

Run the following command to integrate the POST method with the Lambda function and deploy the API Gateway:

```bash
awslocal apigateway put-integration --rest-api-id $API_ID --resource-id $UPLOAD_RESOURCE_ID --http-method POST --type AWS_PROXY --integration-http-method POST --uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:333333333333:function:CommonLambda/invocations
awslocal apigateway create-deployment --rest-api-id $API_ID --stage-name prod
```

Add the permission to the Lambda function to be invoked by the API Gateway:

```bash
awslocal lambda add-permission \
                --function-name CommonLambda \
                --statement-id 1 \
                --action lambda:InvokeFunction \
                --principal apigateway.amazonaws.com \
                --source-arn "arn:aws:execute-api:us-east-1:333333333333:$API_ID/*/*/*" \
                --source-account 333333333333
```

## Test the setup by invoking the API Gateway endpoint and checking the SQS queue and S3 bucket in Account A and Account B:

Create a virtual environment and install the required packages:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

Run the following command to test the setup:

```bash
pytest tests/test_api.py
```
