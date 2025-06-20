import json
import re
import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
import hashlib

logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class ChunkConfig:
    chunk_size: int = 1000
    overlap: int = 200
    min_chunk_size: int = 100

class PIISanitizer:
    def __init__(self):
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone_au': r'\b(?:\+61|0)[2-478](?:[ -]?\d){8}\b',
            'tfn': r'\b\d{3}[ -]?\d{3}[ -]?\d{3}\b',
            'abn': r'\b\d{2}[ -]?\d{3}[ -]?\d{3}[ -]?\d{3}\b',
            'credit_card': r'\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b',
            'bsb': r'\b\d{3}[ -]?\d{3}\b',
            'medicare': r'\b\d{4}[ -]?\d{5}[ -]?\d{1}\b'
        }
        
        self.strata_specific_patterns = {
            'lot_owner_name': r'(?:Lot Owner|Owner|Proprietor):\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            'unit_address': r'Unit\s+\d+[A-Z]?/\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave)',
        }
    
    def sanitize(self, text: str) -> Tuple[str, Dict[str, int]]:
        redaction_counts = {}
        
        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                redaction_counts[pii_type] = len(matches)
                text = re.sub(pattern, f'[{pii_type.upper()}_REDACTED]', text)
        
        for context_type, pattern in self.strata_specific_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                redaction_counts[context_type] = len(matches)
                if context_type == 'lot_owner_name':
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]
                        text = text.replace(match, '[OWNER_NAME_REDACTED]')
        
        return text, redaction_counts

class TextChunker:
    def __init__(self, config: ChunkConfig = ChunkConfig()):
        self.config = config
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_words = sentence.split()
            sentence_size = len(sentence_words)
            
            if current_size + sentence_size > self.config.chunk_size:
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(self._create_chunk_metadata(chunk_text, len(chunks)))
                    
                    overlap_words = current_chunk[-(self.config.overlap):]
                    current_chunk = overlap_words + sentence_words
                    current_size = len(current_chunk)
                else:
                    current_chunk = sentence_words
                    current_size = sentence_size
            else:
                current_chunk.extend(sentence_words)
                current_size += sentence_size
        
        if current_chunk and current_size >= self.config.min_chunk_size:
            chunk_text = ' '.join(current_chunk)
            chunks.append(self._create_chunk_metadata(chunk_text, len(chunks)))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        sentence_endings = r'[.!?]\s+'
        sentences = re.split(sentence_endings, text)
        
        clean_sentences = []
        for sentence in sentences:
            if sentence.strip():
                if not sentence[-1] in '.!?':
                    sentence += '.'
                clean_sentences.append(sentence.strip())
        
        return clean_sentences
    
    def _create_chunk_metadata(self, text: str, index: int) -> Dict[str, Any]:
        return {
            'text': text,
            'index': index,
            'word_count': len(text.split()),
            'char_count': len(text),
            'hash': hashlib.md5(text.encode()).hexdigest()
        }

class ChunkProcessor:
    def __init__(self):
        self.sanitizer = PIISanitizer()
        self.chunker = TextChunker()
    
    def process(self, text: str, tenant_id: str, document_id: str) -> Dict[str, Any]:
        sanitized_text, redaction_counts = self.sanitizer.sanitize(text)
        
        chunks = self.chunker.chunk_text(sanitized_text)
        
        enriched_chunks = []
        for chunk in chunks:
            enriched_chunks.append({
                'chunk_id': f"{document_id}_chunk_{chunk['index']}",
                'text': chunk['text'],
                'metadata': {
                    'index': chunk['index'],
                    'word_count': chunk['word_count'],
                    'char_count': chunk['char_count'],
                    'hash': chunk['hash'],
                    'tenant_id': tenant_id,
                    'document_id': document_id
                }
            })
        
        return {
            'chunks': enriched_chunks,
            'statistics': {
                'total_chunks': len(chunks),
                'total_words': sum(c['word_count'] for c in chunks),
                'total_chars': sum(c['char_count'] for c in chunks),
                'redaction_counts': redaction_counts
            }
        }

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"Processing document chunks for tenant: {event.get('tenantId')}")
    
    text = event.get('text', '')
    tenant_id = event['tenantId']
    document_id = event['documentId']
    
    if not text:
        return {
            'statusCode': 400,
            'error': 'No text provided for chunking'
        }
    
    processor = ChunkProcessor()
    result = processor.process(text, tenant_id, document_id)
    
    logger.info(f"Created {result['statistics']['total_chunks']} chunks with {result['statistics']['redaction_counts']} redactions")
    
    return {
        'statusCode': 200,
        'tenantId': tenant_id,
        'documentId': document_id,
        'chunks': [chunk['text'] for chunk in result['chunks']],
        'chunkMetadata': result['chunks'],
        'totalChunks': result['statistics']['total_chunks'],
        'statistics': result['statistics']
    }