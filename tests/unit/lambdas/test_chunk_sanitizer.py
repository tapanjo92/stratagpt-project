import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../backend/lambdas/chunk-sanitizer'))
from index import handler, PIISanitizer, TextChunker, ChunkConfig, ChunkProcessor

class TestPIISanitizer:
    
    @pytest.fixture
    def sanitizer(self):
        return PIISanitizer()
    
    def test_email_redaction(self, sanitizer):
        text = "Contact me at john.doe@example.com for details"
        sanitized, counts = sanitizer.sanitize(text)
        
        assert "[EMAIL_REDACTED]" in sanitized
        assert "john.doe@example.com" not in sanitized
        assert counts['email'] == 1
    
    def test_australian_phone_redaction(self, sanitizer):
        text = "Call me on 0412 345 678 or +61 412 345 678"
        sanitized, counts = sanitizer.sanitize(text)
        
        assert sanitized.count("[PHONE_AU_REDACTED]") == 2
        assert counts['phone_au'] == 2
    
    def test_tfn_redaction(self, sanitizer):
        text = "My TFN is 123 456 789"
        sanitized, counts = sanitizer.sanitize(text)
        
        assert "[TFN_REDACTED]" in sanitized
        assert "123 456 789" not in sanitized
        assert counts['tfn'] == 1
    
    def test_abn_redaction(self, sanitizer):
        text = "ABN: 12 345 678 901"
        sanitized, counts = sanitizer.sanitize(text)
        
        assert "[ABN_REDACTED]" in sanitized
        assert counts['abn'] == 1
    
    def test_multiple_pii_types(self, sanitizer):
        text = """
        Owner: John Smith
        Email: john@example.com
        Phone: 0412345678
        TFN: 123456789
        """
        sanitized, counts = sanitizer.sanitize(text)
        
        assert "[EMAIL_REDACTED]" in sanitized
        assert "[PHONE_AU_REDACTED]" in sanitized
        assert "[TFN_REDACTED]" in sanitized
        assert sum(counts.values()) >= 3

class TestTextChunker:
    
    @pytest.fixture
    def chunker(self):
        return TextChunker(ChunkConfig(chunk_size=10, overlap=2))
    
    def test_basic_chunking(self, chunker):
        text = " ".join([f"word{i}" for i in range(30)])
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 1
        assert all(chunk['word_count'] <= 10 for chunk in chunks)
    
    def test_chunk_overlap(self, chunker):
        text = " ".join([f"word{i}" for i in range(20)])
        chunks = chunker.chunk_text(text)
        
        if len(chunks) > 1:
            # Check that chunks have overlap
            first_chunk_words = chunks[0]['text'].split()
            second_chunk_words = chunks[1]['text'].split()
            
            overlap = set(first_chunk_words[-2:]) & set(second_chunk_words[:2])
            assert len(overlap) > 0
    
    def test_sentence_preservation(self):
        chunker = TextChunker(ChunkConfig(chunk_size=50, overlap=10))
        text = "This is the first sentence. This is the second sentence. This is the third sentence."
        
        chunks = chunker.chunk_text(text)
        
        for chunk in chunks:
            assert chunk['text'].endswith('.')
    
    def test_chunk_metadata(self, chunker):
        text = "Test text for chunking"
        chunks = chunker.chunk_text(text)
        
        for i, chunk in enumerate(chunks):
            assert chunk['index'] == i
            assert 'word_count' in chunk
            assert 'char_count' in chunk
            assert 'hash' in chunk

class TestChunkProcessor:
    
    @pytest.fixture
    def processor(self):
        return ChunkProcessor()
    
    def test_process_with_pii(self, processor):
        text = "Contact john@example.com or call 0412345678"
        result = processor.process(text, 'tenant-123', 'doc-456')
        
        assert result['statistics']['redaction_counts']['email'] == 1
        assert result['statistics']['redaction_counts']['phone_au'] == 1
        
        for chunk in result['chunks']:
            assert "[EMAIL_REDACTED]" in chunk['text']
            assert "[PHONE_AU_REDACTED]" in chunk['text']
            assert chunk['metadata']['tenant_id'] == 'tenant-123'
            assert chunk['metadata']['document_id'] == 'doc-456'

class TestHandler:
    
    @pytest.fixture
    def valid_event(self):
        return {
            'text': 'This is a test document with multiple sentences. ' * 100,
            'tenantId': 'tenant-123',
            'documentId': 'doc-456'
        }
    
    def test_handler_success(self, valid_event):
        result = handler(valid_event, None)
        
        assert result['statusCode'] == 200
        assert result['tenantId'] == 'tenant-123'
        assert result['documentId'] == 'doc-456'
        assert result['totalChunks'] > 0
        assert 'chunks' in result
        assert 'statistics' in result
    
    def test_handler_no_text(self):
        event = {
            'tenantId': 'tenant-123',
            'documentId': 'doc-456'
        }
        
        result = handler(event, None)
        
        assert result['statusCode'] == 400
        assert 'error' in result
    
    def test_handler_empty_text(self):
        event = {
            'text': '',
            'tenantId': 'tenant-123',
            'documentId': 'doc-456'
        }
        
        result = handler(event, None)
        
        assert result['statusCode'] == 400
        assert 'error' in result