import json
import boto3
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import os

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('dynamoDBTableName'))

def lambda_handler(event, context):
    bucket = event['bucket']
    key = event['key']
    
    try:
        # Get the file from S3
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()
        
        # Handle .docx files
        if key.lower().endswith('.docx'):
            text = extract_docx_text(content)
        else:
            # Decode text content for other file types
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = content.decode('latin-1')
                except UnicodeDecodeError:
                    text = "Unable to decode text file"
        
        # Store plaintext in DynamoDB immediately
        table.update_item(
            Key={'Name': key, 'Bucket': bucket},
            UpdateExpression='SET Plaintext = :plaintext',
            ExpressionAttributeValues={':plaintext': text.strip()}
        )
        
        # Calculate word count
        word_count = len(text.strip().split()) if text.strip() else 0
        
        return {
            'bucket': bucket,
            'key': key,
            'wordCount': word_count
        }
        
    except Exception as e:
        return {
            'bucket': bucket,
            'key': key,
            'summary': f"Error reading file: {str(e)}"
        }

def extract_docx_text(content):
    """Extract text from .docx file content"""
    try:
        # .docx files are zip archives
        with zipfile.ZipFile(BytesIO(content), 'r') as docx:
            # Read the main document XML
            xml_content = docx.read('word/document.xml')
            
        # Parse XML and extract text
        root = ET.fromstring(xml_content)
        
        # Define namespace
        namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        
        # Extract all text elements
        text_elements = root.findall('.//w:t', namespace)
        text = '\n'.join([elem.text for elem in text_elements if elem.text])
        
        return text if text else "No text found in document"
        
    except Exception as e:
        return f"Error extracting .docx text: {str(e)}"