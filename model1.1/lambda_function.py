import json
import boto3
import pickle
import io
import uuid
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
classifications_table = dynamodb.Table('Classifications')
audit_table = dynamodb.Table('AuditLog')

MODEL_BUCKET = 'fyp-hospital-s3-bucket'
MODEL_KEY = 'model/model.pkl'

def load_model():
    print("Loading model from S3...")
    response = s3.get_object(Bucket=MODEL_BUCKET, Key=MODEL_KEY)
    model = pickle.loads(response['Body'].read())
    print("Model loaded!")
    return model

model = load_model()

def lambda_handler(event, context):
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        file_key = event['Records'][0]['s3']['object']['key']
        file_size = event['Records'][0]['s3']['object']['size']

        # Skip model files
        if file_key.startswith('models/'):
            return {'statusCode': 200, 'body': 'Skipped model file'}

        print(f"New file uploaded: {file_key}")

        # Get file text and classify
        file_obj = s3.get_object(Bucket=bucket, Key=file_key)
        file_text = file_obj['Body'].read().decode('utf-8', errors='ignore')

        prediction = model.predict([file_text])[0]
        confidence = float(max(model.predict_proba([file_text])[0]))

        print(f"Classification: {prediction} ({confidence:.4f})")

        # Write to DynamoDB
        classification_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        classifications_table.put_item(
            Item={
                'ClassificationId': classification_id,
                'fileKey': file_key,
                'bucket': bucket,
                'fileSize': file_size,
                'uploadTimestamp': timestamp,
                'status': 'CLASSIFIED',
                'accessLevel': prediction,
                'confidence': str(confidence),
                'classifiedBy': 'ML_SKLEARN'
            }
        )

        audit_table.put_item(
            Item={
                'AuditId': str(uuid.uuid4()),
                'timestamp': timestamp,
                'action': 'UPLOAD',
                'fileKey': file_key,
                'classificationId': classification_id,
                'status': 'CLASSIFIED',
                'accessLevel': prediction
            }
        )

        print(f"Classification record created: {classification_id}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'fileKey': file_key,
                'classification': prediction,
                'confidence': confidence
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }