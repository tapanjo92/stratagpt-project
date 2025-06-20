import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../backend/lambdas/embeddings-generator'))
from index import handler, EmbeddingGenerator, OpenSearchClient, EmbeddingConfig

class TestEmbeddingGenerator:
    
    @pytest.fixture
    def mock_bedrock(self):
        with patch('index.bedrock') as mock:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps({
                'embedding': [0.1] * 768
            })
            mock.invoke_model.return_value = {'body': mock_response}
            yield mock
    
    @pytest.fixture
    def generator(self):
        return EmbeddingGenerator()
    
    def test_generate_embedding_success(self, generator, mock_bedrock):
        embedding = generator.generate_embedding("Test text")
        
        assert embedding is not None
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)
        
        mock_bedrock.invoke_model.assert_called_once()
        call_args = mock_bedrock.invoke_model.call_args
        assert call_args[1]['modelId'] == 'amazon.titan-embed-text-v2:0'
    
    def test_generate_embedding_failure(self, generator, mock_bedrock):
        mock_bedrock.invoke_model.side_effect = Exception("Bedrock error")
        
        embedding = generator.generate_embedding("Test text")
        
        assert embedding is None
    
    def test_generate_batch_embeddings(self, generator, mock_bedrock):
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = generator.generate_batch_embeddings(texts)
        
        assert len(embeddings) == 3
        assert all(len(emb) == 768 for emb in embeddings if emb)
        assert mock_bedrock.invoke_model.call_count == 3

class TestOpenSearchClient:
    
    @pytest.fixture
    def mock_session(self):
        with patch('index.requests.Session') as mock:
            yield mock.return_value
    
    @pytest.fixture
    def client(self):
        return OpenSearchClient('https://test.opensearch.com')
    
    def test_create_index_already_exists(self, client, mock_session):
        mock_session.head.return_value.status_code = 200
        
        result = client.create_index_if_not_exists('tenant-123')
        
        assert result is True
        mock_session.head.assert_called_once()
    
    def test_create_index_new(self, client, mock_session):
        mock_session.head.side_effect = Exception("Not found")
        mock_session.put.return_value.status_code = 201
        
        result = client.create_index_if_not_exists('tenant-123')
        
        assert result is True
        mock_session.put.assert_called_once()
        
        put_call = mock_session.put.call_args
        assert 'strata-tenant-123' in put_call[0][0]
        
        # Check index mapping
        mapping = put_call[1]['json']
        assert mapping['settings']['index']['knn'] is True
        assert mapping['mappings']['properties']['embedding']['dimension'] == 768
    
    def test_index_document_success(self, client, mock_session):
        mock_session.put.return_value.status_code = 201
        
        doc = {
            'tenant_id': 'tenant-123',
            'text': 'Test document',
            'embedding': [0.1] * 768
        }
        
        result = client.index_document('strata-tenant-123', 'doc-1', doc)
        
        assert result is True
        mock_session.put.assert_called_once()
    
    def test_bulk_index_success(self, client, mock_session):
        mock_response = Mock()
        mock_response.json.return_value = {
            'errors': False,
            'items': [{'index': {'_id': '1', 'status': 201}}]
        }
        mock_session.post.return_value = mock_response
        
        documents = [
            {'chunk_id': 'chunk-1', 'text': 'Text 1'},
            {'chunk_id': 'chunk-2', 'text': 'Text 2'}
        ]
        
        result = client.bulk_index('strata-tenant-123', documents)
        
        assert result['success'] is True
        assert result['items_processed'] == 1
        
        # Check bulk format
        bulk_call = mock_session.post.call_args
        bulk_data = bulk_call[1]['data']
        assert 'chunk-1' in bulk_data
        assert 'Text 1' in bulk_data

class TestHandler:
    
    @pytest.fixture
    def mock_env(self):
        with patch.dict(os.environ, {
            'OPENSEARCH_ENDPOINT': 'https://test.opensearch.com',
            'METADATA_TABLE_NAME': 'test-metadata-table'
        }):
            yield
    
    @pytest.fixture
    def valid_event(self):
        return {
            'chunks': ['Chunk 1', 'Chunk 2', 'Chunk 3'],
            'chunkMetadata': [
                {'metadata': {'index': 0, 'word_count': 2}},
                {'metadata': {'index': 1, 'word_count': 2}},
                {'metadata': {'index': 2, 'word_count': 2}}
            ],
            'tenantId': 'tenant-123',
            'documentId': 'doc-456'
        }
    
    @patch('index.OpenSearchClient')
    @patch('index.EmbeddingGenerator')
    def test_handler_success(self, mock_generator_class, mock_client_class, mock_env, valid_event):
        # Setup mocks
        mock_generator = mock_generator_class.return_value
        mock_generator.generate_batch_embeddings.return_value = [[0.1] * 768] * 3
        
        mock_client = mock_client_class.return_value
        mock_client.create_index_if_not_exists.return_value = True
        mock_client.bulk_index.return_value = {
            'success': True,
            'items_processed': 3
        }
        
        result = handler(valid_event, None)
        
        assert result['statusCode'] == 200
        assert result['indexedChunks'] == 3
        assert result['totalChunks'] == 3
        assert result['success'] is True
        
        mock_generator.update_processing_status.assert_called()
        mock_client.create_index_if_not_exists.assert_called_with('tenant-123')
        mock_client.bulk_index.assert_called_once()
    
    def test_handler_no_chunks(self, mock_env):
        event = {
            'tenantId': 'tenant-123',
            'documentId': 'doc-456'
        }
        
        result = handler(event, None)
        
        assert result['statusCode'] == 400
        assert 'error' in result
    
    def test_handler_no_opensearch_endpoint(self):
        event = {
            'chunks': ['Chunk 1'],
            'tenantId': 'tenant-123',
            'documentId': 'doc-456'
        }
        
        result = handler(event, None)
        
        assert result['statusCode'] == 500
        assert 'error' in result
        assert 'OpenSearch endpoint' in result['error']