import json
import boto3
import os

def handler(event, context):
    body = json.loads(event.get("body"))
    account = body.get("account")
    region = body.get("region")
    content = body.get("content")
    filename = body.get("filename")

    s3 = boto3.client("s3", region_name=region)
    sqs = boto3.client("sqs", region_name=region)

    bucket_name = f"team-bucket-{account}"
    queue_name = f"team-queue-{account}"

    s3.put_object(
        Bucket=bucket_name,
        Key=filename,
        Body=content
    )
    
    queue_url = sqs.get_queue_url(
        QueueName=queue_name,
        QueueOwnerAWSAccountId=account
    ).get("QueueUrl")

    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=f"File {filename} uploaded to bucket {bucket_name}"
    )

    response_body = {
        "account": account,
        "region": region,
        "bucket_name": bucket_name,
        "bucket_key": filename,
        "queue_url": queue_url,
    }
    return {
        "statusCode": 200,
        "body": json.dumps(response_body)
    }


