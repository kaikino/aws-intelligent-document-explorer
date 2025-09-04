# Intelligent Document Processing with AWS Textract and Step Functions

This pattern demonstrates a serverless document processing system that automatically extracts text from uploaded documents, generates AI-powered summaries, and provides a web dashboard for file management.

## Architecture

The system uses AWS Step Functions to orchestrate a parallel processing workflow:

- **File Upload**: Users upload documents via a web dashboard using S3 presigned URLs
- **Parallel Processing**: Step Functions splits into metadata extraction and content processing branches
- **Intelligent Routing**: Files are routed to appropriate processors based on type (PDF/images → Textract, text files → direct extraction)
- **Fallback Processing**: Failed Textract extractions automatically fall back to Rekognition for visual analysis
- **AI Summarization**: Long documents (>25 words) get AI-generated summaries via Amazon Comprehend
- **Error Handling**: Comprehensive error catching ensures no uploaded document is ever lost

## Features

- **Multi-format Support**: PDF, images (PNG, JPG, JPEG, TIFF), and text files (TXT, CSV, JSON, XML, LOG)
- **Intelligent Processing**: Automatic routing based on file type and content analysis
- **AI-Powered Summaries**: Amazon Comprehend generates summaries for long documents
- **Visual Fallback**: Amazon Rekognition provides object detection when text extraction fails
- **Web Dashboard**: Upload, view, download, and delete files with extracted text preview
- **Zero Document Loss**: Failed processing creates "Unprocessed" records for easy retry
- **Real-time Monitoring**: CloudWatch dashboard and alarms for system health

## Services Used

- **AWS Step Functions**: Workflow orchestration with parallel processing
- **Amazon Textract**: OCR and document text extraction
- **Amazon Comprehend**: AI-powered text summarization
- **Amazon Rekognition**: Visual content analysis and object detection
- **AWS Lambda**: Serverless compute for processing functions
- **Amazon S3**: Document storage with presigned URL uploads
- **Amazon DynamoDB**: Metadata and results storage
- **Amazon API Gateway**: REST API for web dashboard
- **Amazon SQS**: Asynchronous Textract job polling
- **Amazon EventBridge**: S3 event triggering

## Deployment

### Prerequisites

- AWS CLI configured with appropriate permissions
- AWS SAM CLI installed
- Python 3.13 or later

### Deploy

1. Clone the repository:
```bash
git clone <repository-url>
cd intelligent-document-explorer-sam
```

2. Deploy the stack:
```bash
sam deploy --guided
```

3. Note the outputs for the web dashboard URL and API endpoint.

### Configuration

The deployment creates:
- S3 bucket for document storage
- DynamoDB table for metadata and results
- Step Functions state machine for processing workflow
- Lambda functions for each processing step
- API Gateway for web interface
- CloudWatch dashboard and alarms

## Usage

1. **Access Dashboard**: Open the WebsiteURL from the deployment outputs
2. **Upload Files**: Use the web interface to upload documents (up to 5GB)
3. **View Results**: Files appear in the dashboard with processing status and summaries
4. **Download Files**: Click the download button to get original files
5. **View Extracted Text**: Click the "T" button to see full extracted text
6. **Delete Files**: Remove files and their associated data

## Cost Optimization

The system uses a pay-per-use model with costs primarily driven by:
- **Amazon Textract**: ~$1.50 per 1,000 pages (dominant cost)
- **Amazon DynamoDB**: Storage and request costs
- **AWS Step Functions**: State transition costs
- **AWS Lambda**: Minimal compute costs

Key optimizations:
- Text files bypass expensive Textract processing
- Short documents skip AI summarization
- Intelligent fallback reduces failed processing costs
- Right-sized Lambda memory allocations

## Monitoring

The deployment includes:
- CloudWatch dashboard with performance and request metrics
- Alarms for Step Functions failures, API Gateway errors, and Lambda errors
- Log groups with appropriate retention periods
- Cost tracking and optimization recommendations

## Security

- S3 buckets use presigned URLs for secure file access
- IAM roles follow least-privilege principles
- All data encrypted in transit and at rest
- API Gateway enforces HTTPS
- No sensitive data in Step Functions logs

## Cleanup

1. Empty S3 buckets:
```bash
aws s3 rm s3://<bucket-name> --recursive
```

2. Delete the stack:
```bash
sam delete
```

## Step Functions Workflow

The document processing workflow orchestrates parallel processing with intelligent routing:

**Input**: `{bucket, key}` from S3 upload event

**Parallel Processing**:
- **Content Processing Branch**: Extracts and analyzes document content
- **Metadata Extraction Branch**: Stores file metadata in DynamoDB

**Intelligent File Routing**:
- **PDF/Images** → Textract OCR processing
- **Text Files** (TXT, CSV, JSON, XML, LOG) → Direct S3 text extraction
- **Unsupported Files** → Marked as unprocessed

**Text Extraction Flow**:
1. **Textract Path**: StartTextract → WaitForTextract (SQS polling) → TextractPoller
2. **Fallback**: If Textract fails → Rekognition visual analysis
3. **Plain Text Path**: Direct S3 file reading for text formats
4. **Storage**: All extracted text stored in DynamoDB with word count

**AI Summarization**:
- **Long Documents** (>25 words) → Amazon Comprehend AI summary
- **Short Documents** (≤25 words) → Plain text copied as summary

**Error Handling**: Any processing failures create "Unprocessed" records for manual retry

**Result**: Every uploaded file gets a DynamoDB record with metadata, extracted text, and AI-generated summary

---

**Important**: This application uses various AWS services with associated costs. See the AWS Pricing page for details. You are responsible for any AWS costs incurred.

## License

This project is licensed under the MIT-0 License.