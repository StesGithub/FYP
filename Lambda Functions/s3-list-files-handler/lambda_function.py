import json
import boto3

s3_client = boto3.client('s3')
BUCKET_NAME = 'fyp-hospital-s3-bucket'

def lambda_handler(event, context):
 
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        
        files = []
        for obj in response.get('Contents', []):
            files.append({
                'fileName': obj['Key'],
                'size': f"{round(obj['Size'] / 1024, 2)} KB",
                'lastModified': obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
            })

        return {
            'statusCode': 200,
            'body': json.dumps(files)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }