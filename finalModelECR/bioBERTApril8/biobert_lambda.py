import json
import boto3
import torch
import uuid
from datetime import datetime
from urllib.parse import unquote_plus
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
classifications_table = dynamodb.Table('Classifications')
audit_table = dynamodb.Table('AuditLog')

BUCKET_NAME = 'fyp-hospital-s3-bucket'
MODEL_PATH = './biobert_model_final'
CONFIDENCE_THRESHOLD = .70

cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST'
}

LABELS = {0: 'PUBLIC', 1: 'INTERNAL', 2: 'RESTRICTED'}

# Load model on cold start
print("Loading BioBERT model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=3)
model.eval()
print("BioBERT model loaded!")

def classify_text(text):
    inputs = tokenizer(
        text,
        return_tensors='pt',
        truncation=True,
        max_length=512,
        padding=True
    )
    with torch.no_grad():
        outputs = model(**inputs)
        probabilities = F.softmax(outputs.logits, dim=1)
        predicted_class = torch.argmax(probabilities, dim=1).item()
        confidence = probabilities[0][predicted_class].item()

    return LABELS[predicted_class], confidence

def lambda_handler(event, context):
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        file_key = unquote_plus(event['Records'][0]['s3']['object']['key'])
        file_size = event['Records'][0]['s3']['object']['size']

        if file_key.startswith('models/') or file_key.startswith('model/'):
            return {'statusCode': 200, 'body': 'Skipped model file'}

        print(f"New file uploaded: {file_key}")

        file_obj = s3.get_object(Bucket=bucket, Key=file_key)
        file_text = file_obj['Body'].read().decode('utf-8', errors='ignore')

        prediction, confidence = classify_text(file_text)

        if confidence < CONFIDENCE_THRESHOLD:
            print(f"Low confidence ({confidence:.4f}) classifying as QUARANTINE")
            prediction = 'QUARANTINE'


        print(f"Classification: {prediction} ({confidence:.4f})")

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
                'classifiedBy': 'ML_BIOBERT'
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
                'accessLevel': prediction,
                'classifiedBy': 'ML_BIOBERT'
            }
        )

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