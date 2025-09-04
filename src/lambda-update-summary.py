import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('dynamoDBTableName'))

def lambda_handler(event, context):
    bucket = event['bucket']
    key = event['key']
    
    try:
        # Get plaintext from DynamoDB and copy to summary (for short texts)
        response = table.get_item(Key={'Name': key, 'Bucket': bucket})
        plaintext = response.get('Item', {}).get('Plaintext', 'Unsupported file type')
        
        # Update item with summary = plaintext
        table.update_item(
            Key={
                'Name': key,
                'Bucket': bucket
            },
            UpdateExpression='SET Summary = :summary',
            ExpressionAttributeValues={
                ':summary': plaintext
            }
        )
        
        return {
            'statusCode': 200,
            'message': 'Summary updated successfully'
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'error': str(e)
        }