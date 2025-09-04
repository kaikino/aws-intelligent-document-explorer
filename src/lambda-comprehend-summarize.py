import json
import boto3
import os

client = boto3.client('comprehend')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('dynamoDBTableName'))

def lambda_handler(event, context):
    bucket = event['bucket']
    key = event['key']
    
    # Get plaintext from DynamoDB
    response = table.get_item(Key={'Name': key, 'Bucket': bucket})
    plaintext = response['Item']['Plaintext']
    
    # Use Comprehend to summarize text
    comprehend_response = client.detect_key_phrases(
        Text=plaintext,
        LanguageCode='en'
    )
    
    # Extract key phrases and create summary
    key_phrases = [phrase['Text'] for phrase in comprehend_response['KeyPhrases'][:15]]
    summary = ', '.join(key_phrases)
    
    # Ensure summary is under 15 words
    words = summary.split()
    if len(words) > 15:
        summary = ' '.join(words[:15])
    
    # Store summary directly in DynamoDB
    table.update_item(
        Key={'Name': key, 'Bucket': bucket},
        UpdateExpression='SET Summary = :summary',
        ExpressionAttributeValues={':summary': summary}
    )
    
    return {
        'bucket': bucket,
        'key': key
    }