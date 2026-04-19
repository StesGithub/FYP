import json
import boto3
from boto3.dynamodb.conditions import Key
from urllib.parse import unquote_plus

dynamodb = boto3.resource('dynamodb')
classifications_table = dynamodb.Table('Classifications')
audit_table = dynamodb.Table('AuditLog')
s3_client = boto3.client('s3')

BUCKET_NAME = 'fyp-hospital-s3-bucket'

cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,GET'
}

# Access control matrix
ACCESS_MATRIX = {
    'RESTRICTED': ['Doctor'],
    'INTERNAL':   ['Doctor', 'Nurse', 'Admin'],
    'PUBLIC':     ['Doctor', 'Nurse', 'Admin', 'Facilities'],
    'QUARANTINE': ['Admin']
}

def get_user_role(event):
    try:
        # Extract Cognito groups from JWT token claims
        claims = event['requestContext']['authorizer']['claims']
        groups = claims.get('cognito:groups', '')
        if isinstance(groups, str):
            groups = groups.strip('[]').split(',')
        return [g.strip() for g in groups if g.strip()]
    except Exception:
        return []

def check_access(user_roles, classification):
    allowed_roles = ACCESS_MATRIX.get(classification, [])
    for role in user_roles:
        if role in allowed_roles:
            return True
    return False

def log_access_attempt(file_key, user_roles, classification, access_granted):
    import uuid
    from datetime import datetime
    try:
        audit_table.put_item(
            Item={
                'AuditId': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'ACCESS',
                'fileKey': file_key,
                'userRoles': str(user_roles),
                'classificationChecked': classification,
                'accessGranted': access_granted
            }
        )
    except Exception as e:
        print(f"Audit log error: {str(e)}")

def lambda_handler(event, context):

    print(f"Full event: {json.dumps(event)}")
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }

        # Get file key from query parameters
        params = event.get('queryStringParameters') or {}
        print(f"Params: {params}")
        print(f"Full event keys: {list(event.keys())}")
        file_key = unquote_plus(params.get('fileKey', ''))
        print(f"File key: {file_key}")
    
        if not file_key:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps('Missing fileKey parameter')
            }

        # Get user role from Cognito token
        user_roles = get_user_role(event)
        print(f"User roles: {user_roles}")
        print(f"Requesting access to: {file_key}")

        # Look up file classification in DynamoDB
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
        access_granted = check_access(user_roles, access_level)

        # Log the access attempt
        log_access_attempt(file_key, user_roles, access_level, access_granted)

        if access_granted:
            # Generate pre-signed URL for download
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': file_key},
                ExpiresIn=300  # 5 minutes
            )
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'accessGranted': True,
                    'fileKey': file_key,
                    'accessLevel': access_level,
                    'downloadUrl': url,
                    'expiresIn': '5 minutes'
                })
            }
        else:
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({
                    'accessGranted': False,
                    'fileKey': file_key,
                    'accessLevel': access_level,
                    'message': f'Access denied. Your role does not have permission to access {access_level} documents.'
                })
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps(f'Error: {str(e)}')
        }