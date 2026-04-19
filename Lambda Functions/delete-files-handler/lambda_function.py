import json
import boto3
import uuid
from datetime import datetime
from urllib.parse import unquote_plus

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
classifications_table = dynamodb.Table('Classifications')
audit_table = dynamodb.Table('AuditLog')

BUCKET_NAME = 'fyp-hospital-s3-bucket'

cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,DELETE'
}

# Delete permissions matrix
DELETE_MATRIX = {
    'RESTRICTED': ['Doctor'],
    'INTERNAL':   ['Doctor', 'Admin'],
    'PUBLIC':     ['Doctor', 'Admin', 'Facilities'],
    'QUARANTINE': ['Admin']
}

def get_user_role(event):
    try:
        claims = event['requestContext']['authorizer']['claims']
        groups = claims.get('cognito:groups', '')
        if isinstance(groups, list):
            return groups
        if isinstance(groups, str):
            groups = groups.strip('[]').replace('"', '').split(',')
            return [g.strip() for g in groups if g.strip()]
        return []
    except Exception as e:
        print(f"Role extraction error: {str(e)}")
        return []

def check_delete_permission(user_roles, classification):
    
    return True

def lambda_handler(event, context):
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }

        # Get file key from query parameters
        params = event.get('queryStringParameters') or {}
        file_key = unquote_plus(params.get('fileKey', ''))

        if not file_key:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps('Missing fileKey parameter')
            }

        # Get user role
        user_roles = get_user_role(event)
        print(f"User roles: {user_roles}")
        print(f"Requesting deletion of: {file_key}")

        # Look up classification in DynamoDB
        result = classifications_table.scan(
            FilterExpression='fileKey = :fk',
            ExpressionAttributeValues={':fk': file_key}
        )

        items = result.get('Items', [])

        if not items:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps('File classification not found')
            }

        # Get most recent classification
        classification = sorted(
            items,
            key=lambda x: x.get('uploadTimestamp', ''),
            reverse=True
        )[0]

        access_level = classification.get('accessLevel', 'QUARANTINE')
        classification_id = classification.get('ClassificationId')

        # Check delete permission
        can_delete = check_delete_permission(user_roles, access_level)

        timestamp = datetime.utcnow().isoformat()

        if not can_delete:
            # Log denied deletion attempt
            audit_table.put_item(
                Item={
                    'AuditId': str(uuid.uuid4()),
                    'timestamp': timestamp,
                    'action': 'DELETE_DENIED',
                    'fileKey': file_key,
                    'userRoles': str(user_roles),
                    'accessLevel': access_level,
                    'accessGranted': False
                }
            )
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({
                    'deleted': False,
                    'message': f'Access denied. Your role does not have permission to delete {access_level} documents.'
                })
            }

        # Delete from S3
        s3.delete_object(Bucket=BUCKET_NAME, Key=file_key)
        print(f"Deleted from S3: {file_key}")

        # Update DynamoDB classification record
        classifications_table.update_item(
            Key={'ClassificationId': classification_id},
            UpdateExpression='SET #s = :s, deletedAt = :d, deletedBy = :r',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':s': 'DELETED',
                ':d': timestamp,
                ':r': str(user_roles)
            }
        )

        # Write audit log
        audit_table.put_item(
            Item={
                'AuditId': str(uuid.uuid4()),
                'timestamp': timestamp,
                'action': 'DELETE',
                'fileKey': file_key,
                'classificationId': classification_id,
                'userRoles': str(user_roles),
                'accessLevel': access_level,
                'accessGranted': True
            }
        )

        print(f"Deletion complete: {file_key}")

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'deleted': True,
                'fileKey': file_key,
                'message': f'{file_key} successfully deleted'
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps(f'Error: {str(e)}')
        }