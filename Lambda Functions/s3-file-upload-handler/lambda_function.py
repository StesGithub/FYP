import json
import boto3
import base64


s3_client = boto3.client('s3')
BUCKET_NAME = 'fyp-hospital-s3-bucket'

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        file_content = base64.b64decode(body['file'])
        file_name = body['fileName']

        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
            Body=file_content
        )

        return {
            'statusCode': 200,
            'body': json.dumps('File uploaded successfully!')
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps('Error uploading file!')
        }   
