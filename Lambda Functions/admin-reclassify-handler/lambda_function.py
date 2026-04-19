import json
import boto3
import uuid
from datetime import datetime
from urllib.parse import unquote_plus

dynamodb = boto3.resource('dynamodb')
classifications_table = dynamodb.Table('Classifications')
audit_table = dynamodb.Table('AuditLog')

cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST'
}

VALID_CLASSIFICATIONS = ['RESTRICTED', 'INTERNAL', 'PUBLIC', 'QUARANTINE']

def get_user_role(event):
    print(f"Full event keys: {list(event.keys())}")
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

def lambda_handler(event, context):
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }

        # Get user role
        user_roles = get_user_role(event)
        print(f"User roles: {user_roles}")

        # Only Admin can reclassify
        if 'Admin' not in user_roles:
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps('Access denied. Only Admin users can reclassify documents.')
            }

        # Get request body
        body = json.loads(event.get('body', '{}'))
        file_key = body.get('fileKey', '')
        new_classification = body.get('newClassification', '').upper()
        reason = body.get('reason', 'Manual admin override')

        if not file_key or not new_classification:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps('Missing fileKey or newClassification')
            }

        if new_classification not in VALID_CLASSIFICATIONS:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps(f'Invalid classification. Must be one of: {VALID_CLASSIFICATIONS}')
            }

        # Find the classification record
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

        old_classification = classification.get('accessLevel', 'UNKNOWN')
        classification_id = classification.get('ClassificationId')

        timestamp = datetime.utcnow().isoformat()

        # Update classification
        classifications_table.update_item(
            Key={'ClassificationId': classification_id},
            UpdateExpression='SET accessLevel = :new, classifiedBy = :cb, reclassifiedAt = :t, reclassificationReason = :r, previousClassification = :old',
            ExpressionAttributeValues={
                ':new': new_classification,
                ':cb': 'HUMAN_OVERRIDE',
                ':t': timestamp,
                ':r': reason,
                ':old': old_classification
            }
        )

        # Write audit log
        audit_table.put_item(
            Item={
                'AuditId': str(uuid.uuid4()),
                'timestamp': timestamp,
                'action': 'RECLASSIFY',
                'fileKey': file_key,
                'classificationId': classification_id,
                'oldClassification': old_classification,
                'newClassification': new_classification,
                'classifiedBy': 'HUMAN_OVERRIDE',
                'userRoles': str(user_roles),
                'reason': reason
            }
        )

        print(f"Reclassified {file_key}: {old_classification} → {new_classification}")

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'fileKey': file_key,
                'oldClassification': old_classification,
                'newClassification': new_classification,
                'message': f'Successfully reclassified {file_key} from {old_classification} to {new_classification}'
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps(f'Error: {str(e)}')
        }