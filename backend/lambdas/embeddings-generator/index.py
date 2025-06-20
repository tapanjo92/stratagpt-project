import json
import boto3
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import time
from dataclasses import dataclass
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

@dataclass
class EmbeddingConfig:
    model_id: str = 'amazon.titan-embed-text-v2:0'
    dimensions: int = 768
    normalize: bool = True
    batch_size: int = 10

class OpenSearchClient:
    def __init__(self, endpoint: str, region: str = 'ap-southeast-2'):
        self.endpoint = endpoint.rstrip('/')
        self.region = region
        self.session = requests.Session()
        
    def create_index_if_not_exists(self, tenant_id: str) -> bool:
        index_name = f"strata-{tenant_id}"
        
        try:
            response = self.session.head(f"{self.endpoint}/{index_name}")
            if response.status_code == 200:
                logger.info(f"Index {index_name} already exists")
                return True
        except:
            pass
        
        index_mapping = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "knn": True
                }
            },
            "mappings": {
                "properties": {
                    "tenant_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "text": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 768,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 16
                            }
                        }
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "word_count": {"type": "integer"},
                            "char_count": {"type": "integer"},
                            "index": {"type": "integer"},
                            "hash": {"type": "keyword"}
                        }
                    },
                    "timestamp": {"type": "date"},
                    "upload_date": {"type": "date"}
                }
            }
        }
        
        try:
            response = self.session.put(
                f"{self.endpoint}/{index_name}",
                json=index_mapping,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Created index {index_name}")
                return True
            else:
                logger.error(f"Failed to create index: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            return False
    
    def index_document(self, index_name: str, doc_id: str, document: Dict[str, Any]) -> bool:
        try:
            response = self.session.put(
                f"{self.endpoint}/{index_name}/_doc/{doc_id}",
                json=document,
                headers={'Content-Type': 'application/json'}
            )
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            return False
    
    def bulk_index(self, index_name: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        bulk_data = []
        
        for doc in documents:
            action = {"index": {"_index": index_name, "_id": doc['chunk_id']}}
            bulk_data.append(json.dumps(action))
            bulk_data.append(json.dumps(doc))
        
        bulk_body = '\n'.join(bulk_data) + '\n'
        
        try:
            response = self.session.post(
                f"{self.endpoint}/_bulk",
                data=bulk_body,
                headers={'Content-Type': 'application/x-ndjson'}
            )
            
            result = response.json()
            return {
                'success': not result.get('errors', True),
                'items_processed': len(result.get('items', [])),
                'response': result
            }
            
        except Exception as e:
            logger.error(f"Bulk index error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class EmbeddingGenerator:
    def __init__(self, config: EmbeddingConfig = EmbeddingConfig()):
        self.config = config
        self.metadata_table = dynamodb.Table(os.environ.get('METADATA_TABLE_NAME', 'strata-document-metadata'))
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        try:
            response = bedrock.invoke_model(
                modelId=self.config.model_id,
                body=json.dumps({
                    'inputText': text,
                    'dimensions': self.config.dimensions,
                    'normalize': self.config.normalize
                })
            )
            
            result = json.loads(response['body'].read())
            return result.get('embedding')
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return None
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        embeddings = []
        
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            
            for text in batch:
                embedding = self.generate_embedding(text)
                embeddings.append(embedding)
                time.sleep(0.1)
        
        return embeddings
    
    def update_processing_status(self, tenant_id: str, document_id: str, status: str, indexed_count: int):
        try:
            self.metadata_table.update_item(
                Key={
                    'tenantId': tenant_id,
                    'documentId': document_id
                },
                UpdateExpression='SET embeddingStatus = :status, indexedChunks = :count, lastUpdated = :timestamp',
                ExpressionAttributeValues={
                    ':status': status,
                    ':count': indexed_count,
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update status: {str(e)}")

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"Generating embeddings for document: {event.get('documentId')}")
    
    chunks = event.get('chunks', [])
    chunk_metadata = event.get('chunkMetadata', [])
    tenant_id = event['tenantId']
    document_id = event['documentId']
    
    if not chunks:
        return {
            'statusCode': 400,
            'error': 'No chunks provided for embedding generation'
        }
    
    opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
    if not opensearch_endpoint:
        return {
            'statusCode': 500,
            'error': 'OpenSearch endpoint not configured'
        }
    
    generator = EmbeddingGenerator()
    opensearch = OpenSearchClient(opensearch_endpoint)
    
    if not opensearch.create_index_if_not_exists(tenant_id):
        return {
            'statusCode': 500,
            'error': 'Failed to create OpenSearch index'
        }
    
    generator.update_processing_status(tenant_id, document_id, 'generating_embeddings', 0)
    
    embeddings = generator.generate_batch_embeddings(chunks)
    
    documents_to_index = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        if embedding:
            metadata = chunk_metadata[i]['metadata'] if i < len(chunk_metadata) else {}
            
            doc = {
                'tenant_id': tenant_id,
                'document_id': document_id,
                'chunk_id': f"{document_id}_chunk_{i}",
                'text': chunk,
                'embedding': embedding,
                'metadata': metadata,
                'timestamp': datetime.utcnow().isoformat(),
                'upload_date': datetime.utcnow().isoformat()
            }
            
            documents_to_index.append(doc)
    
    index_name = f"strata-{tenant_id}"
    result = opensearch.bulk_index(index_name, documents_to_index)
    
    indexed_count = result.get('items_processed', 0) if result.get('success') else 0
    
    generator.update_processing_status(
        tenant_id, 
        document_id, 
        'completed' if result.get('success') else 'failed',
        indexed_count
    )
    
    logger.info(f"Indexed {indexed_count} chunks for document {document_id}")
    
    return {
        'statusCode': 200 if result.get('success') else 500,
        'tenantId': tenant_id,
        'documentId': document_id,
        'indexedChunks': indexed_count,
        'totalChunks': len(chunks),
        'success': result.get('success', False)
    }