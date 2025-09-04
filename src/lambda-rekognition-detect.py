import json
import boto3
import os

rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('dynamoDBTableName'))

def lambda_handler(event, context):
    bucket = event['bucket']
    key = event['key']
    
    try:
        response = rekognition.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            MaxLabels=10,
            MinConfidence=70
        )
        
        # Extract labels and create summary
        labels = [label['Name'] for label in response['Labels']]
        summary = ', '.join(labels[:5])  # Top 5 labels
        
        # Store plaintext in DynamoDB immediately
        plaintext = summary if summary else 'No objects detected'
        table.update_item(
            Key={'Name': key, 'Bucket': bucket},
            UpdateExpression='SET Plaintext = :plaintext',
            ExpressionAttributeValues={':plaintext': plaintext}
        )
        
        # Calculate word count
        word_count = len(plaintext.split()) if plaintext else 0
        
        return {
            'bucket': bucket,
            'key': key,
            'wordCount': word_count
        }
        
    except Exception as e:
        error_msg = f'Error detecting objects: {str(e)}'
        table.update_item(
            Key={'Name': key, 'Bucket': bucket},
            UpdateExpression='SET Plaintext = :plaintext',
            ExpressionAttributeValues={':plaintext': error_msg}
        )
        
        return {
            'bucket': bucket,
            'key': key,
            'wordCount': 0
        }