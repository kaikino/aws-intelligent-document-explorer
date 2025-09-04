import json
import boto3
import base64
import os
from decimal import Decimal

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('dynamoDBTableName'))

def lambda_handler(event, context):
    print(f"Lambda invoked with event: {json.dumps(event)}")
    
    method = event.get('httpMethod', 'UNKNOWN')
    path = event.get('path', 'UNKNOWN')
    
    print(f"Method: {method}, Path: {path}")
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS'
    }
    
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers}
    
    try:
        if method == 'GET' and path == '/':
            print("Serving dashboard")
            return serve_dashboard(headers)
        elif method == 'GET' and path == '/home':
            print("Serving HTML")
            return serve_html(headers)
        elif method == 'POST' and path == '/upload':
            print("Handling upload")
            return handle_upload(event, headers)
        elif method == 'GET' and path == '/files':
            print("Getting files")
            return handle_get_files(headers)
        elif method == 'POST' and path == '/presigned-url':
            print("Getting presigned URL")
            return get_presigned_url(event, headers)
        elif method == 'DELETE' and '/delete/' in path:
            print("Deleting file")
            return handle_delete(event, headers)
        elif method == 'GET' and '/download/' in path:
            print("Downloading file")
            return handle_download(event, headers)
        elif method == 'GET' and '/plaintext/' in path:
            print("Getting plaintext")
            return handle_get_plaintext(event, headers)
        else:
            print(f"No route found for {method} {path}")
            print(f"Full event: {json.dumps(event)}")
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Not found: {method} {path}',
                    'debug': {
                        'method': method,
                        'path': path,
                        'resource': event.get('resource'),
                        'pathParameters': event.get('pathParameters')
                    }
                })
            }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def handle_upload(event, headers):
    try:
        print(f"Upload request received")
        print(f"Headers: {event.get('headers', {})}")
        print(f"Has body: {'body' in event}")
        print(f"Body length: {len(event.get('body', '')) if event.get('body') else 0}")
        print(f"Is base64: {event.get('isBase64Encoded', False)}")
        
        if not event.get('body'):
            print("No body in request")
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No file data received'})
            }
        
        # Get boundary from content-type header
        content_type = event.get('headers', {}).get('content-type', '') or event.get('headers', {}).get('Content-Type', '')
        print(f"Content-Type: {content_type}")
        
        if 'boundary=' not in content_type:
            print("No boundary found")
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': f'No boundary found in content-type: {content_type}'})
            }
        
        boundary = content_type.split('boundary=')[1]
        print(f"Boundary: {boundary}")
        
        # Decode the body
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(event['body'])
        else:
            body = event['body'].encode('utf-8')
        
        print(f"Body length: {len(body)}")
        
        # Split by boundary
        boundary_bytes = f'--{boundary}'.encode()
        parts = body.split(boundary_bytes)
        print(f"Found {len(parts)} parts")
        
        bucket = os.environ.get('BUCKET_NAME')
        
        for i, part in enumerate(parts):
            print(f"Processing part {i}, length: {len(part)}")
            if b'Content-Disposition: form-data' in part and b'filename=' in part:
                print(f"Found file part {i}")
                
                # Extract filename
                lines = part.split(b'\r\n')
                filename = 'uploaded_file'
                
                for line in lines:
                    if b'filename=' in line:
                        start = line.find(b'filename="') + 10
                        end = line.find(b'"', start)
                        if start > 9 and end > start:
                            filename = line[start:end].decode('utf-8')
                        print(f"Extracted filename: {filename}")
                        break
                
                # Skip empty filenames
                if not filename or filename == '""':
                    continue
                
                # Find file content (after double CRLF)
                content_start = part.find(b'\r\n\r\n')
                if content_start != -1:
                    file_content = part[content_start + 4:]
                    # Remove trailing CRLF if present
                    if file_content.endswith(b'\r\n'):
                        file_content = file_content[:-2]
                    
                    print(f"File content length: {len(file_content)}")
                    
                    # Skip empty files
                    if len(file_content) == 0:
                        continue
                    
                    # Upload to S3
                    s3.put_object(
                        Bucket=bucket,
                        Key=filename,
                        Body=file_content
                    )
                    
                    print(f"File uploaded: {filename}")
                    
                    return {
                        'statusCode': 200,
                        'headers': headers,
                        'body': json.dumps({'message': f'File {filename} uploaded successfully'})
                    }
        
        print("No valid files found in any part")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'No valid files found in request'})
        }
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Upload failed: {str(e)}'})
        }

def serve_html(headers):
    html = '''<html><head><title>Home</title></head><body><h1>Document Processing System</h1><p><a href="/">View Dashboard</a></p><p><a href="/files">View Files API</a></p></body></html>'''
    
    response = {
        'statusCode': 200,
        'headers': {**headers, 'Content-Type': 'text/html'},
        'body': html
    }
    print(f"Returning simple HTML response")
    return response

def serve_dashboard(headers):
    try:
        response = table.scan()
        files = []
        for item in response['Items']:
            converted_item = {}
            for key, value in item.items():
                if isinstance(value, Decimal):
                    converted_item[key] = float(value)
                else:
                    converted_item[key] = value
            files.append(converted_item)
        
        # Sort files by date (newest first)
        files.sort(key=lambda x: x.get('TimeUploaded', ''), reverse=True)
        
        files_html = ''.join([
            f'''<div class="file-card">
                <div class="file-row">
                    <div class="file-info">
                        <div class="file-header">
                            <div class="file-name">{file.get('Name', 'Unknown')}</div>
                            <div class="file-meta">
                                <span class="meta-type">{file.get('FileType', 'Unknown').upper()}</span>
                                <span class="meta-size">{'%.1fKB' % (file.get('FileSize', 0)/1024) if file.get('FileSize', 0) < 1024*1024 else '%.1fMB' % (file.get('FileSize', 0)/1024/1024)}</span>
                                <span class="meta-date">{file.get('TimeUploaded', 'Unknown')[:19].replace('T', ' ') if file.get('TimeUploaded') else 'Unknown'}</span>
                            </div>
                        </div>
                        <div class="file-summary">{file.get('Summary', 'Processing...')}</div>
                    </div>
                    <div>
                        <button class="btn btn-secondary" onclick="showPlaintext('{file.get('Name', '')}')" style="margin-right: 5px; padding: 6px 12px; font-size: 1rem; width: 32px;">T</button>
                        <button class="btn btn-primary" onclick="downloadFile('{file.get('Name', '')}')" style="margin-right: 5px; padding: 6px 12px; font-size: 1rem; width: 32px;">↓</button>
                        <button class="btn btn-danger" onclick="deleteFile('{file.get('Name', '')}')" style="padding: 6px 12px; font-size: 1rem; width: 32px;">&times;</button>
                    </div>
                </div>
            </div>'''
            for file in files
        ])
        
        html = f'''<html><head><meta charset="UTF-8"><title>Intelligent Document Explorer</title>
        <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #2c3e50; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .header h1 {{ color: #2c3e50; font-size: 2.5rem; margin-bottom: 10px; }}
        .header p {{ color: #7f8c8d; font-size: 1.1rem; }}
        .upload-section {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .upload-area {{ border: 3px dashed #3498db; border-radius: 8px; padding: 40px; text-align: center; transition: all 0.3s; }}
        .upload-area:hover {{ border-color: #2980b9; background: #f8f9fa; }}
        .upload-area input {{ margin-bottom: 20px; }}
        .btn {{ padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; transition: all 0.3s; }}
        .btn-primary {{ background: #3498db; color: white; }}
        .btn-primary:hover {{ background: #2980b9; transform: translateY(-1px); }}
        .btn-secondary {{ background: #6c757d; color: white; }}
        .btn-secondary:hover {{ background: #5a6268; }}
        .btn-danger {{ background: #e74c3c; color: white; padding: 6px 12px; font-size: 0.9rem; }}
        .btn-danger:hover {{ background: #c0392b; }}
        .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }}
        .modal-content {{ background: white; margin: 5% auto; padding: 20px; border-radius: 8px; width: 80%; max-width: 800px; max-height: 80%; overflow-y: auto; }}
        .close {{ float: right; font-size: 28px; font-weight: bold; cursor: pointer; }}
        .close:hover {{ color: #999; }}
        .files-section {{ background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .files-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .file-grid {{ display: grid; gap: 15px; }}
        .file-card {{ background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 12px 16px; transition: all 0.2s; }}
        .file-card:hover {{ background: #e9ecef; }}
        .file-row {{ display: flex; justify-content: space-between; align-items: center; }}
        .file-info {{ flex: 1; }}
        .file-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }}
        .file-name {{ font-weight: 600; color: #2c3e50; font-size: 1rem; }}
        .file-meta {{ display: flex; gap: 15px; color: #7f8c8d; font-size: 0.85rem; margin-right: 10px; }}
        .meta-type {{ min-width: 60px; text-align: right; }}
        .meta-size {{ min-width: 70px; text-align: right; }}
        .meta-date {{ min-width: 140px; text-align: right; }}
        .file-summary {{ color: #666; font-size: 0.9rem; font-style: italic; margin-top: 4px; line-height: 1.4; }}
        .status {{ margin: 15px 0; padding: 12px; border-radius: 6px; }}
        .success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
        .empty-state {{ text-align: center; padding: 60px 20px; color: #7f8c8d; }}
        .empty-state i {{ font-size: 3rem; margin-bottom: 20px; }}
        </style></head>
        <body>
        <div class="container">
            <div class="header">
                <h1>Intelligent Document Explorer</h1>
                <p>Upload and analyze your documents with AI-powered text extraction</p>
            </div>
            
            <div class="upload-section">
                <div class="upload-area">
                    <h3>Upload Documents</h3>
                    <p style="margin: 10px 0; color: #7f8c8d;">Drag & drop files or click to browse</p>
                    <input type="file" id="fileInput" multiple style="margin: 20px 0;">
                    <br>
                    <button class="btn btn-primary" onclick="uploadFiles()">Upload Files</button>
                    <div id="uploadStatus"></div>
                </div>
            </div>
            
            <div class="files-section">
                <div class="files-header">
                    <h3>Processed Files ({len(files)})</h3>
                </div>
                <div class="file-grid" id="filesList">
                {files_html if files else '<div class="empty-state"><h3>No files yet</h3><p>Upload some documents to get started</p></div>'}
        
        <script>
        async function downloadFile(filename) {{
            window.open('/Prod/download/' + encodeURIComponent(filename), '_blank');
        }}
        
        async function showPlaintext(filename) {{
            try {{
                const response = await fetch('/Prod/plaintext/' + encodeURIComponent(filename));
                const data = await response.json();
                
                document.getElementById('modalTitle').textContent = 'Extracted Text - ' + filename;
                document.getElementById('modalText').textContent = data.plaintext || 'No text available';
                document.getElementById('plaintextModal').style.display = 'block';
            }} catch (error) {{
                alert('Error loading plaintext: ' + error.message);
            }}
        }}
        
        function closeModal() {{
            document.getElementById('plaintextModal').style.display = 'none';
        }}
        
        async function deleteFile(filename) {{
            if (!confirm('Are you sure you want to delete ' + filename + '?')) return;
            
            try {{
                const response = await fetch('/Prod/delete/' + encodeURIComponent(filename), {{
                    method: 'DELETE'
                }});
                
                if (response.ok) {{
                    window.location.reload();
                }} else {{
                    alert('Failed to delete file');
                }}
            }} catch (error) {{
                alert('Error deleting file: ' + error.message);
            }}
        }}
        </script>
                </div>
            </div>
        </div>
        
        <!-- Modal for plaintext -->
        <div id="plaintextModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeModal()">&times;</span>
                <h3 id="modalTitle">Extracted Text</h3>
                <pre id="modalText" style="white-space: pre-wrap; font-family: monospace; background: #f8f9fa; padding: 15px; border-radius: 4px;"></pre>
            </div>
        </div>
        
        <script>
        async function uploadFiles() {{
            const files = document.getElementById('fileInput').files;
            const status = document.getElementById('uploadStatus');
            
            if (files.length === 0) {{
                status.innerHTML = '<div class="error">Please select files to upload</div>';
                return;
            }}
            
            status.innerHTML = '<div>Uploading ' + files.length + ' files...</div>';
            let successCount = 0;
            
            for (let file of files) {{
                try {{
                    // Get presigned URL
                    const urlResponse = await fetch('/Prod/presigned-url', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            'filename': file.name,
                            'contentType': file.type || 'application/octet-stream'
                        }})
                    }});
                    
                    if (!urlResponse.ok) {{
                        console.error('Failed to get upload URL for:', file.name);
                        continue;
                    }}
                    
                    const urlData = await urlResponse.json();
                    
                    // Upload directly to S3
                    const uploadResponse = await fetch(urlData.uploadUrl, {{
                        method: 'PUT',
                        body: file,
                        headers: {{
                            'Content-Type': file.type
                        }}
                    }});
                    
                    if (uploadResponse.ok) {{
                        successCount++;
                        console.log('Uploaded:', file.name);
                    }} else {{
                        console.error('Upload failed for:', file.name, 'Status:', uploadResponse.status);
                    }}
                }} catch (error) {{
                    console.error('Upload error for', file.name, ':', error);
                }}
            }}
            
            status.innerHTML = '<div class="success">Uploaded ' + successCount + ' of ' + files.length + ' files successfully!</div>';
            
            status.innerHTML = '<div class="success">Files uploaded! Processing... Refresh in 3 seconds.</div>';
            document.getElementById('fileInput').value = '';
            
            setTimeout(() => {{
                window.location.reload();
            }}, 3000);
        }}
        </script>
        </body></html>'''
        
        return {
            'statusCode': 200,
            'headers': {**headers, 'Content-Type': 'text/html'},
            'body': html
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {**headers, 'Content-Type': 'text/html'},
            'body': f'<html><body><h1>Error</h1><p>{str(e)}</p></body></html>'
        }

def handle_get_files(headers):
    response = table.scan()
    
    # Convert Decimal to float for JSON serialization
    items = []
    for item in response['Items']:
        converted_item = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                converted_item[key] = float(value)
            else:
                converted_item[key] = value
        items.append(converted_item)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'files': items})
    }

def get_presigned_url(event, headers):
    try:
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename', 'uploaded_file')
        content_type = body.get('contentType', 'application/octet-stream')
        
        bucket = os.environ.get('BUCKET_NAME')
        
        # Generate presigned URL for PUT operation with conditions
        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket, 
                'Key': filename,
                'ContentType': content_type
            },
            ExpiresIn=3600  # 1 hour
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'uploadUrl': presigned_url,
                'filename': filename,
                'contentType': content_type
            })
        }
        
    except Exception as e:
        print(f"Presigned URL error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def handle_delete(event, headers):
    try:
        import urllib.parse
        
        # Extract filename from path /delete/{filename}
        path = event['path']
        delete_prefix = '/delete/'
        
        if delete_prefix not in path:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid delete path'})
            }
        
        # Get filename after /delete/ and decode URL encoding
        filename_encoded = path.split(delete_prefix, 1)[1]
        filename = urllib.parse.unquote(filename_encoded)
        bucket = os.environ.get('BUCKET_NAME')
        
        print(f"Deleting file: {filename} from bucket: {bucket}")
        
        # Delete from S3
        s3.delete_object(Bucket=bucket, Key=filename)
        
        # Delete from DynamoDB
        table.delete_item(
            Key={
                'Name': filename,
                'Bucket': bucket
            }
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': f'File {filename} deleted successfully'})
        }
        
    except Exception as e:
        print(f"Delete error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def handle_get_plaintext(event, headers):
    try:
        import urllib.parse
        
        # Extract filename from path /plaintext/{filename}
        path = event['path']
        plaintext_prefix = '/plaintext/'
        
        if plaintext_prefix not in path:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid plaintext path'})
            }
        
        # Get filename after /plaintext/ and decode URL encoding
        filename_encoded = path.split(plaintext_prefix, 1)[1]
        filename = urllib.parse.unquote(filename_encoded)
        bucket = os.environ.get('BUCKET_NAME')
        
        print(f"Getting plaintext for: {filename} from bucket: {bucket}")
        
        # Get plaintext from DynamoDB
        response = table.get_item(
            Key={
                'Name': filename,
                'Bucket': bucket
            }
        )
        
        print(f"DynamoDB response: {response}")
        item = response.get('Item', {})
        print(f"Item: {item}")
        plaintext = item.get('Plaintext', 'No text available')
        print(f"Plaintext: {plaintext[:100] if plaintext else 'None'}...")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'plaintext': plaintext})
        }
        
    except Exception as e:
        print(f"Plaintext error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def handle_download(event, headers):
    try:
        import urllib.parse
        
        # Extract filename from path /download/{filename}
        path = event['path']
        download_prefix = '/download/'
        
        if download_prefix not in path:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid download path'})
            }
        
        # Get filename after /download/ and decode URL encoding
        filename_encoded = path.split(download_prefix, 1)[1]
        filename = urllib.parse.unquote(filename_encoded)
        bucket = os.environ.get('BUCKET_NAME')
        
        print(f"Generating download URL for: {filename}")
        
        # Generate presigned URL for download
        download_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': filename},
            ExpiresIn=3600  # 1 hour
        )
        
        # Redirect to the presigned URL
        return {
            'statusCode': 302,
            'headers': {
                **headers,
                'Location': download_url
            },
            'body': ''
        }
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }