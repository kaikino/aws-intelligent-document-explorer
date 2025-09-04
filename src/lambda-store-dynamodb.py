import json
import boto3
import os
import decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('dynamoDBTableName'))

def lambda_handler(event, context):
    # Handle error cases where bucket/key might not be available
    if 'bucket' in event and 'key' in event:
        record = {
            'Name': event['key'],
            'Bucket': event['bucket'],
            'Summary': event['summary']
        }
        table.put_item(Item=json.loads(json.dumps(record), parse_float=decimal.Decimal))
        return {
            'statusCode': 200,
            'message': 'Data stored successfully'
        }
    else:
        # Error case - log the error but don't try to store without bucket/key
        print(f"Error occurred: {event.get('error', 'Unknown')} - {event.get('cause', 'No cause')}")
        return {
            'statusCode': 200,
            'message': 'Error logged - no file context available'
        }