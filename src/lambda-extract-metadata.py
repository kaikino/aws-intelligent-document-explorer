import json
import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('dynamoDBTableName'))

def lambda_handler(event, context):
    bucket = event['bucket']
    key = event['key']
    
    try:
        # Get file metadata from S3
        response = s3.head_object(Bucket=bucket, Key=key)
        
        # Extract file extension
        file_type = key.split('.')[-1].lower() if '.' in key else 'unknown'
        
        # Update metadata in DynamoDB
        table.update_item(
            Key={
                'Name': key,
                'Bucket': bucket
            },
            UpdateExpression='SET FileType = :file_type, FileSize = :file_size, TimeUploaded = :time_uploaded',
            ExpressionAttributeValues={
                ':file_type': file_type,
                ':file_size': response['ContentLength'],
                ':time_uploaded': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            }
        )
        
        return {
            'bucket': bucket,
            'key': key,
            'metadata': 'stored'
        }
        
    except Exception as e:
        return {
            'bucket': bucket,
            'key': key,
            'error': str(e)
        }