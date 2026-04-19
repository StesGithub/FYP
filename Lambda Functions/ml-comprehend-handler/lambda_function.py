import json
import boto3
import uuid
from datetime import datetime
from urllib.parse import unquote_plus

s3 = boto3.client('s3')
comprehend_medical = boto3.client('comprehendmedical', region_name='eu-west-1')
dynamodb = boto3.resource('dynamodb')
classifications_table = dynamodb.Table('Classifications')
audit_table = dynamodb.Table('AuditLog')

def lambda_handler(event, context):
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        file_key = unquote_plus(event['Records'][0]['s3']['object']['key'])
        file_size = event['Records'][0]['s3']['object']['size']

        # Skip model files
        if file_key.startswith('models/') or file_key.startswith('model/'):
            return {'statusCode': 200, 'body': 'Skipped model file'}

        print(f"New file uploaded: {file_key}")

        # Get file text from S3
        file_obj = s3.get_object(Bucket=bucket, Key=file_key)
        file_text = file_obj['Body'].read().decode('utf-8', errors='ignore')

        # Truncate to 20000 characters (Comprehend Medical limit)
        file_text = file_text[:20000]

        # Run PHI detection
        phi_response = comprehend_medical.detect_phi(Text=file_text)
        phi_entities = phi_response['Entities']

        # Run medical entity detection
        entity_response = comprehend_medical.detect_entities_v2(Text=file_text)
        medical_entities = entity_response['Entities']

        # Determine classification based on PHI
        if len(phi_entities) > 0:
            classification = 'RESTRICTED'
            confidence = max([e['Score'] for e in phi_entities])
        elif len(medical_entities) > 0:
            confidence = max([e['Score'] for e in medical_entities])
            if confidence >= 0.70:
                classification = 'RESTRICTED'
            else:
                # Low confidence medical entities — could be incidental terminology
                classification = 'INTERNAL'
        else:
            classification = 'PUBLIC'
            confidence = 0.0


        avg_confidence = sum([e['Score'] for e in phi_entities + medical_entities]) / len(phi_entities + medical_entities) if (phi_entities + medical_entities) else 1.0
        if avg_confidence < 0.70 and classification not in ['PUBLIC']:
            classification = 'QUARANTINE'
        
        phi_values = [e['Text'] for e in phi_entities]
        med_values = [e['Text'] for e in medical_entities]

        # Use .join() on the extracted strings
        print(f"PHI entities found: {len(phi_entities)} - {', '.join(phi_values)}")
        print(f"Medical entities found: {len(medical_entities)} - {', '.join(med_values)}")
        print(f"Classification: {classification} ({confidence:.4f})")


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
                'accessLevel': classification,
                'confidence': str(confidence),
                'classifiedBy': 'ML_COMPREHEND',
                'phiEntitiesFound': len(phi_entities),
                'medicalEntitiesFound': len(medical_entities)
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
                'accessLevel': classification,
                'classifiedBy': 'ML_COMPREHEND'
            }
        )

        print(f"Classification record created: {classification_id}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'fileKey': file_key,
                'classification': classification,
                'confidence': confidence,
                'phiEntities': len(phi_entities),
                'medicalEntities': len(medical_entities)
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }