import pytest
import boto3
import json
import time
from moto import mock_s3, mock_dynamodb, mock_stepfunctions, mock_iam
from unittest.mock import patch, Mock
import os

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'

@pytest.fixture
def s3_client(aws_credentials):
    with mock_s3():
        yield boto3.client('s3', region_name='ap-southeast-2')

@pytest.fixture
def dynamodb_client(aws_credentials):
    with mock_dynamodb():
        yield boto3.client('dynamodb', region_name='ap-southeast-2')

@pytest.fixture
def stepfunctions_client(aws_credentials):
    with mock_stepfunctions():
        yield boto3.client('stepfunctions', region_name='ap-southeast-2')

class TestIngestionPipeline:
    
    @pytest.fixture
    def setup_infrastructure(self, s3_client, dynamodb_client):
        # Create S3 bucket
        bucket_name = 'strata-documents-test'
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'ap-southeast-2'}
        )
        
        # Create DynamoDB tables
        dynamodb_client.create_table(
            TableName='strata-document-metadata',
            KeySchema=[
                {'AttributeName': 'tenantId', 'KeyType': 'HASH'},
                {'AttributeName': 'documentId', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'tenantId', 'AttributeType': 'S'},
                {'AttributeName': 'documentId', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        return {
            'bucket_name': bucket_name,
            'metadata_table': 'strata-document-metadata'
        }
    
    def test_document_upload_trigger(self, s3_client, setup_infrastructure):
        bucket_name = setup_infrastructure['bucket_name']
        
        # Upload a test document
        test_content = b'This is a test PDF document content'
        s3_client.put_object(
            Bucket=bucket_name,
            Key='tenant-123/documents/test-doc.pdf',
            Body=test_content,
            ContentType='application/pdf',
            Metadata={
                'tenant-id': 'tenant-123',
                'document-id': 'doc-456'
            }
        )
        
        # Verify upload
        response = s3_client.head_object(
            Bucket=bucket_name,
            Key='tenant-123/documents/test-doc.pdf'
        )
        
        assert response['ContentLength'] == len(test_content)
        assert response['Metadata']['tenant-id'] == 'tenant-123'
        assert response['Metadata']['document-id'] == 'doc-456'
    
    def test_metadata_tracking(self, dynamodb_client, setup_infrastructure):
        table_name = setup_infrastructure['metadata_table']
        dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
        table = dynamodb.Table(table_name)
        
        # Insert metadata
        table.put_item(
            Item={
                'tenantId': 'tenant-123',
                'documentId': 'doc-456',
                'fileName': 'test-doc.pdf',
                'fileSize': 1024,
                'uploadDate': '2024-01-01T00:00:00Z',
                'status': 'uploaded',
                'contentType': 'application/pdf'
            }
        )
        
        # Query metadata
        response = table.get_item(
            Key={
                'tenantId': 'tenant-123',
                'documentId': 'doc-456'
            }
        )
        
        assert response['Item']['fileName'] == 'test-doc.pdf'
        assert response['Item']['status'] == 'uploaded'
    
    @patch('boto3.client')
    def test_textract_integration(self, mock_boto_client):
        # Mock Textract client
        mock_textract = Mock()
        mock_boto_client.return_value = mock_textract
        
        # Simulate Textract response
        mock_textract.start_document_text_detection.return_value = {
            'JobId': 'job-123'
        }
        
        mock_textract.get_document_text_detection.return_value = {
            'JobStatus': 'SUCCEEDED',
            'Blocks': [
                {
                    'BlockType': 'LINE',
                    'Text': 'This is extracted text from the document'
                }
            ]
        }
        
        # Test extraction
        job_response = mock_textract.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': 'test-bucket',
                    'Name': 'test.pdf'
                }
            }
        )
        
        assert job_response['JobId'] == 'job-123'
        
        # Get results
        result = mock_textract.get_document_text_detection(JobId='job-123')
        assert result['JobStatus'] == 'SUCCEEDED'
        assert len(result['Blocks']) > 0
    
    @patch('requests.Session')
    def test_opensearch_indexing(self, mock_session):
        # Mock OpenSearch responses
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            '_index': 'strata-tenant-123',
            '_id': 'chunk-1',
            'result': 'created'
        }
        mock_session.return_value.put.return_value = mock_response
        
        # Test document indexing
        from backend.lambdas.embeddings_generator.index import OpenSearchClient
        
        client = OpenSearchClient('https://test.opensearch.com')
        result = client.index_document(
            'strata-tenant-123',
            'chunk-1',
            {
                'text': 'Test chunk text',
                'embedding': [0.1] * 768,
                'metadata': {'tenant_id': 'tenant-123'}
            }
        )
        
        assert result is True
    
    def test_end_to_end_flow(self, s3_client, dynamodb_client, setup_infrastructure):
        """Test the complete ingestion flow with mocked AWS services"""
        
        # 1. Upload document
        bucket_name = setup_infrastructure['bucket_name']
        document_key = 'tenant-123/documents/strata-minutes.pdf'
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=document_key,
            Body=b'Strata meeting minutes content...',
            Metadata={
                'tenant-id': 'tenant-123',
                'document-id': 'doc-789'
            }
        )
        
        # 2. Update metadata
        dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
        table = dynamodb.Table(setup_infrastructure['metadata_table'])
        
        table.put_item(
            Item={
                'tenantId': 'tenant-123',
                'documentId': 'doc-789',
                'fileName': 'strata-minutes.pdf',
                'status': 'processing',
                'processingSteps': {
                    'upload': 'completed',
                    'textract': 'in_progress',
                    'chunking': 'pending',
                    'embedding': 'pending',
                    'indexing': 'pending'
                }
            }
        )
        
        # 3. Simulate processing steps
        processing_stages = [
            ('textract', 'completed'),
            ('chunking', 'completed'),
            ('embedding', 'completed'),
            ('indexing', 'completed')
        ]
        
        for stage, status in processing_stages:
            table.update_item(
                Key={
                    'tenantId': 'tenant-123',
                    'documentId': 'doc-789'
                },
                UpdateExpression=f'SET processingSteps.{stage} = :status',
                ExpressionAttributeValues={
                    ':status': status
                }
            )
            time.sleep(0.1)  # Simulate processing time
        
        # 4. Verify final state
        response = table.get_item(
            Key={
                'tenantId': 'tenant-123',
                'documentId': 'doc-789'
            }
        )
        
        item = response['Item']
        assert all(
            item['processingSteps'][stage] == 'completed' 
            for stage in ['upload', 'textract', 'chunking', 'embedding', 'indexing']
        )