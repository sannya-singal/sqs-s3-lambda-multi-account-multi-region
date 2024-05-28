import pytest
import uuid
import requests
import boto3

def boto3_client():
    def _boto3_client(service_name: str, account_id: str = "333333333333", region_name: str = "us-east-1"):
        return boto3.client(service_name, region_name=region_name, endpoint_url="http://localhost:4566", aws_access_key_id=account_id, aws_secret_access_key=account_id)
    return _boto3_client

class TestAPI:
    @pytest.mark.parametrize(
    "account_id, region_name",
        [
            ("111111111111", "us-east-1"),
            ("222222222222", "eu-west-1")
        ]
    )                       
    def test_api(self, region_name, account_id):
        client = boto3_client()
        apigw_client = client("apigateway")
        
        # rest apis
        response = apigw_client.get_rest_apis()
        apis = response["items"]
        assert len(apis) == 1
        assert apis[0]["name"] == "CommonLambdaApi"

        # api stages
        api_id = apis[0]["id"]
        response = apigw_client.get_stages(restApiId=api_id)
        api_stages = response["item"]
        assert len(api_stages) == 1
        assert api_stages[0]["stageName"] == "prod"
        stage_name = api_stages[0]["stageName"]

        # invoke api
        url = f"https://{api_id}.execute-api.localhost.localstack.cloud:4566/{stage_name}/upload"
        body = {
            "account": account_id,
            "region": region_name,
            "filename": uuid.uuid4().hex,
            "content": "Hello from LocalStack from Team C!"
        }
        response = requests.post(url, json=body)

        assert response.status_code == 200
        response_body = response.json()
        assert response_body["account"] == body["account"]
        assert response_body["region"] == body["region"]

        queue_url = response_body["queue_url"]
        bucket_name = response_body["bucket_name"]
        bucket_key = response_body["bucket_key"]


        # test sqs message
        client = boto3_client()
        sqs_client = client("sqs", account_id=body["account"], region_name=body["region"])
        response = sqs_client.receive_message(QueueUrl=queue_url)
        messages = response.get("Messages", [])
        receipt_handle = response.get("ReceiptHandle", None)
        assert len(messages) == 1
        message = messages[0]
        assert message["Body"] == f"File {bucket_key} uploaded to bucket {bucket_name}"
        # delete message
        if receipt_handle:
            sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)

        # test s3 content
        s3_client = client("s3", account_id=body["account"], region_name=body["region"])
        response = s3_client.get_object(Bucket=bucket_name, Key=bucket_key)
        content = response["Body"].read().decode("utf-8")
        assert content == body["content"]
