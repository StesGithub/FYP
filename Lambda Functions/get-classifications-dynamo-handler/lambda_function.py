import json
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
classifications_table = dynamodb.Table('Classifications')
audit_table = dynamodb.Table('AuditLog')

cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,GET'
}

def lambda_handler(event, context):
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }

        # Get all classifications
        classifications = classifications_table.scan()
        audit_logs = audit_table.scan()

        # Sort by timestamp
        items = sorted(
            classifications['Items'],
            key=lambda x: x.get('uploadTimestamp', ''),
            reverse=True
        )

        # Build summary stats
        total = len(items)
        restricted = len([i for i in items if i.get('accessLevel') == 'RESTRICTED'])
        internal = len([i for i in items if i.get('accessLevel') == 'INTERNAL'])
        public = len([i for i in items if i.get('accessLevel') == 'PUBLIC'])
        quarantine = len([i for i in items if i.get('accessLevel') == 'QUARANTINE'])
        sklearn = len([i for i in items if i.get('classifiedBy') == 'ML_SKLEARN'])
        comprehend = len([i for i in items if i.get('classifiedBy') == 'ML_COMPREHEND'])

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'summary': {
                    'total': total,
                    'restricted': restricted,
                    'internal': internal,
                    'public': public,
                    'quarantine': quarantine,
                    'classifiedBySklearn': sklearn,
                    'classifiedByComprehend': comprehend
                },
                'classifications': items,
                'auditLog': sorted(
                    audit_logs['Items'],
                    key=lambda x: x.get('timestamp', ''),
                    reverse=True
                )
            }, default=str)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps(f'Error: {str(e)}')
        }