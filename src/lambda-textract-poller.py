import json
import boto3
import os

textract = boto3.client('textract')
sqs = boto3.client('sqs')
stepfunctions = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('dynamoDBTableName'))

def lambda_handler(event, context):
    for record in event['Records']:
        message = json.loads(record['body'])
        job_id = message['jobId']
        bucket = message['bucket']
        key = message['key']
        
        try:
            # Check job status
            result = textract.get_document_text_detection(JobId=job_id)
            status = result['JobStatus']
            
            if status == 'SUCCEEDED':
                # Extract plaintext from results
                plaintext = ''
                for block in result.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        plaintext += block['Text'] + '\n'
                
                # Store plaintext in DynamoDB immediately
                table.update_item(
                    Key={'Name': key, 'Bucket': bucket},
                    UpdateExpression='SET Plaintext = :plaintext',
                    ExpressionAttributeValues={':plaintext': plaintext.strip()}
                )
                
                # Calculate word count
                word_count = len(plaintext.strip().split()) if plaintext.strip() else 0
                
                # Continue Step Functions workflow
                stepfunctions.send_task_success(
                    taskToken=message.get('taskToken'),
                    output=json.dumps({
                        'bucket': bucket,
                        'key': key,
                        'wordCount': word_count
                    })
                )
                
            elif status == 'FAILED':
                stepfunctions.send_task_failure(
                    taskToken=message.get('taskToken'),
                    error='TextractFailed',
                    cause=result.get('StatusMessage', 'Unknown error')
                )
                
            else:
                # Still processing, re-queue with delay
                sqs.send_message(
                    QueueUrl=os.environ['SQS_QUEUE_URL'],
                    MessageBody=record['body'],
                    DelaySeconds=10
                )
                
        except Exception as e:
            stepfunctions.send_task_failure(
                taskToken=message.get('taskToken'),
                error='PollingError',
                cause=str(e)
            )