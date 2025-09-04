import json
import boto3
import os

textract = boto3.client('textract')
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    bucket = event['bucket']
    key = event['key']
    
    try:
        response = textract.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            }
        )
        
        job_id = response['JobId']
        
        return {
            'jobId': job_id,
            'bucket': bucket,
            'key': key
        }
        
    except Exception as e:
        return {'error': str(e)}