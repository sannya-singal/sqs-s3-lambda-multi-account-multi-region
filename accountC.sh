export AWS_ACCESS_KEY_ID=333333333333
export AWS_SECRET_ACCESS_KEY=test

awslocal iam create-role --role-name common-lambda-role --assume-role-policy-document file://trust-policy.json
awslocal iam put-role-policy --role-name common-lambda-role --policy-name common-lambda-policy --policy-document file://lambda-policy.json

zip lambda_function.zip lambda_function.py
            
awslocal lambda create-function --function-name CommonLambda \
                --runtime python3.11 \
                --role arn:aws:iam::333333333333:role/common-lambda-role \
                --handler lambda_function.handler \
                --zip-file fileb://lambda_function.zip \
                --timeout 300

awslocal apigateway create-rest-api --name "CommonLambdaApi"

API_ID=$(awslocal apigateway get-rest-apis --query 'items[?name==`CommonLambdaApi`].id' --output text)

RESOURCE_ID=$(awslocal apigateway get-resources --rest-api-id $API_ID --query 'items[?path==`/`].id' --output text)
            
UPLOAD_RESOURCE_ID=$(awslocal apigateway create-resource --rest-api-id $API_ID --parent-id $RESOURCE_ID --path-part upload --query 'id' --output text)

awslocal apigateway put-method --rest-api-id $API_ID --resource-id $UPLOAD_RESOURCE_ID --http-method POST --authorization-type "NONE"

awslocal apigateway put-integration --rest-api-id $API_ID --resource-id $UPLOAD_RESOURCE_ID --http-method POST --type AWS_PROXY --integration-http-method POST --uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:333333333333:function:CommonLambda/invocations

awslocal apigateway create-deployment --rest-api-id $API_ID --stage-name prod

awslocal lambda add-permission \
                --function-name CommonLambda \
                --statement-id 1 \
                --action lambda:InvokeFunction \
                --principal apigateway.amazonaws.com \
                --source-arn "arn:aws:execute-api:us-east-1:333333333333:$API_ID/*/*/*" \
                --source-account 333333333333