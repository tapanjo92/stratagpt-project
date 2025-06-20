import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../backend/lambdas/textract-processor'))
from index import handler, TextractProcessor, DocumentType, TextractRequest

class TestTextractProcessor:
    
    @pytest.fixture
    def mock_aws_services(self):
        with patch('index.textract') as mock_textract, \
             patch('index.s3') as mock_s3, \
             patch('index.dynamodb') as mock_dynamodb:
            yield {
                'textract': mock_textract,
                's3': mock_s3,
                'dynamodb': mock_dynamodb
            }
    
    @pytest.fixture
    def sample_event(self):
        return {
            'bucket': 'test-bucket',
            'key': 'documents/test.pdf',
            'tenantId': 'tenant-123',
            'documentId': 'doc-456'
        }
    
    def test_detect_document_type(self):
        processor = TextractProcessor()
        
        assert processor.detect_document_type('test.pdf') == DocumentType.PDF
        assert processor.detect_document_type('test.PDF') == DocumentType.PDF
        assert processor.detect_document_type('test.docx') == DocumentType.DOCX
        assert processor.detect_document_type('test.tiff') == DocumentType.TIFF
        assert processor.detect_document_type('test.png') == DocumentType.PNG
        assert processor.detect_document_type('test.jpg') == DocumentType.JPEG
        assert processor.detect_document_type('test.unknown') == DocumentType.PDF  # default
    
    def test_extract_text_from_response(self):
        processor = TextractProcessor()
        
        response = {
            'Blocks': [
                {'BlockType': 'PAGE'},
                {'BlockType': 'LINE', 'Text': 'First line'},
                {'BlockType': 'LINE', 'Text': 'Second line'},
                {'BlockType': 'WORD', 'Text': 'Word'}
            ]
        }
        
        result = processor.extract_text_from_response(response)
        assert result == 'First line\nSecond line'
    
    @patch('index.os.environ', {'METADATA_TABLE_NAME': 'test-table'})
    def test_handler_pdf_async(self, mock_aws_services, sample_event):
        mock_textract = mock_aws_services['textract']
        mock_textract.start_document_text_detection.return_value = {
            'JobId': 'job-123'
        }
        
        mock_table = Mock()
        mock_aws_services['dynamodb'].Table.return_value = mock_table
        
        result = handler(sample_event, None)
        
        assert result['statusCode'] == 200
        assert result['jobId'] == 'job-123'
        assert result['tenantId'] == 'tenant-123'
        assert result['documentId'] == 'doc-456'
        assert result['detectionType'] == 'async'
        
        mock_textract.start_document_text_detection.assert_called_once()
        mock_table.update_item.assert_called_once()
    
    @patch('index.os.environ', {'METADATA_TABLE_NAME': 'test-table'})
    def test_handler_image_sync(self, mock_aws_services, sample_event):
        sample_event['key'] = 'documents/test.png'
        
        mock_textract = mock_aws_services['textract']
        mock_textract.detect_document_text.return_value = {
            'Blocks': [
                {'BlockType': 'LINE', 'Text': 'Extracted text'}
            ]
        }
        
        mock_table = Mock()
        mock_aws_services['dynamodb'].Table.return_value = mock_table
        
        result = handler(sample_event, None)
        
        assert result['statusCode'] == 200
        assert result['text'] == 'Extracted text'
        assert result['detectionType'] == 'sync'
        assert result['jobId'] is None
        
        mock_textract.detect_document_text.assert_called_once()
    
    def test_handler_error_handling(self, mock_aws_services, sample_event):
        mock_textract = mock_aws_services['textract']
        mock_textract.start_document_text_detection.side_effect = Exception('AWS Error')
        
        mock_table = Mock()
        mock_aws_services['dynamodb'].Table.return_value = mock_table
        
        with pytest.raises(Exception) as exc_info:
            handler(sample_event, None)
        
        assert str(exc_info.value) == 'AWS Error'
    
    def test_update_metadata_failure(self, mock_aws_services):
        processor = TextractProcessor()
        mock_table = Mock()
        mock_table.update_item.side_effect = Exception('DynamoDB Error')
        processor.metadata_table = mock_table
        
        request = TextractRequest(
            bucket='test-bucket',
            key='test.pdf',
            tenant_id='tenant-123',
            document_id='doc-456',
            document_type=DocumentType.PDF
        )
        
        # Should not raise exception, just log warning
        processor.update_metadata(request, 'job-123', 'async')