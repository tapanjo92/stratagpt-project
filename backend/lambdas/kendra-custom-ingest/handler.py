import json
import boto3
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
kendra = boto3.client('kendra')
dynamodb = boto3.resource('dynamodb')

# Environment variables
KENDRA_INDEX_ID = os.environ['KENDRA_INDEX_ID']
DOCUMENT_TABLE = os.environ.get('DOCUMENT_TABLE', 'strata-documents')

class KendraCustomIngestor:
    def __init__(self):
        self.kendra_index_id = KENDRA_INDEX_ID
        self.doc_table = dynamodb.Table(DOCUMENT_TABLE) if DOCUMENT_TABLE else None
        
    def generate_document_id(self, bucket: str, key: str) -> str:
        """Generate a unique document ID for Kendra"""
        # Use S3 URI as the document ID for consistency
        return f"s3://{bucket}/{key}"
    
    def extract_tenant_id_from_key(self, key: str) -> str:
        """Extract tenant ID from S3 key structure: tenant-id/documents/filename"""
        parts = key.split('/')
        if len(parts) >= 3 and parts[1] == 'documents':
            return parts[0]
        return 'unknown'
    
    def get_document_metadata(self, bucket: str, key: str) -> Dict[str, Any]:
        """Get document metadata from S3 object tags and custom metadata"""
        try:
            # Get S3 object metadata
            response = s3.head_object(Bucket=bucket, Key=key)
            s3_metadata = response.get('Metadata', {})
            
            # Get S3 object tags
            tag_response = s3.get_object_tagging(Bucket=bucket, Key=key)
            tags = {tag['Key']: tag['Value'] for tag in tag_response.get('TagSet', [])}
            
            # Combine metadata and tags
            metadata = {
                'content_type': response.get('ContentType', 'text/plain'),
                'content_length': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified', datetime.utcnow()).isoformat(),
                **s3_metadata,
                **tags
            }
            
            return metadata
        except Exception as e:
            logger.warning(f"Error getting metadata for {bucket}/{key}: {str(e)}")
            return {}
    
    def determine_document_type(self, key: str, metadata: Dict[str, Any]) -> str:
        """Determine document type from metadata or filename"""
        # Check metadata first
        if 'document_type' in metadata:
            return metadata['document_type']
        
        # Infer from filename
        filename = key.split('/')[-1].lower()
        if 'agm' in filename or 'minutes' in filename:
            return 'meeting-minutes'
        elif 'bylaw' in filename or 'by-law' in filename:
            return 'bylaws'
        elif 'capital' in filename or 'works' in filename:
            return 'capital-works'
        elif 'levy' in filename or 'budget' in filename:
            return 'financial'
        elif 'insurance' in filename:
            return 'insurance'
        else:
            return 'general'
    
    def get_document_content(self, bucket: str, key: str) -> tuple[str, str]:
        """Get document content from S3"""
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            # Determine content type
            content_type = response.get('ContentType', 'text/plain')
            
            # For text files, decode to string
            if content_type.startswith('text/') or key.endswith('.txt'):
                try:
                    text_content = content.decode('utf-8')
                    return text_content, 'PLAIN_TEXT'
                except UnicodeDecodeError:
                    # If decode fails, return as binary
                    return content, 'PDF'
            else:
                # For binary files (PDF, DOCX, etc.)
                return content, 'PDF'
                
        except Exception as e:
            logger.error(f"Error reading document {bucket}/{key}: {str(e)}")
            raise
    
    def create_kendra_attributes(self, tenant_id: str, metadata: Dict[str, Any], 
                                document_type: str, s3_uri: str) -> List[Dict[str, Any]]:
        """Create Kendra document attributes"""
        attributes = [
            {
                'Key': 'tenant_id',
                'Value': {
                    'StringValue': tenant_id
                }
            },
            {
                'Key': 'document_type',
                'Value': {
                    'StringValue': document_type
                }
            },
            {
                'Key': '_source_uri',
                'Value': {
                    'StringValue': s3_uri
                }
            },
            {
                'Key': '_category',
                'Value': {
                    'StringValue': document_type
                }
            }
        ]
        
        # Add upload date if available
        if 'upload_date' in metadata:
            attributes.append({
                'Key': 'upload_date',
                'Value': {
                    'DateValue': metadata['upload_date']
                }
            })
        elif 'last_modified' in metadata:
            attributes.append({
                'Key': 'upload_date',
                'Value': {
                    'DateValue': metadata['last_modified']
                }
            })
        
        # Add any custom metadata as attributes
        for key, value in metadata.items():
            if key not in ['document_type', 'tenant_id', 'upload_date', 'last_modified', 
                          'content_type', 'content_length'] and not key.startswith('x-amz-'):
                attributes.append({
                    'Key': key,
                    'Value': {
                        'StringValue': str(value)
                    }
                })
        
        return attributes
    
    def ingest_document(self, bucket: str, key: str) -> Dict[str, Any]:
        """Ingest a single document into Kendra with custom metadata"""
        try:
            # Extract tenant ID
            tenant_id = self.extract_tenant_id_from_key(key)
            
            # Generate document ID
            doc_id = self.generate_document_id(bucket, key)
            
            # Get metadata
            metadata = self.get_document_metadata(bucket, key)
            
            # Determine document type
            document_type = self.determine_document_type(key, metadata)
            
            # Determine content type from file extension
            if key.endswith('.pdf'):
                content_type = 'PDF'
            elif key.endswith('.docx'):
                content_type = 'MS_WORD'
            elif key.endswith('.html') or key.endswith('.htm'):
                content_type = 'HTML'
            else:
                content_type = 'PLAIN_TEXT'
            
            # Extract title from metadata or generate from filename
            title = metadata.get('title', key.split('/')[-1].replace('-', ' ').replace('_', ' ').title())
            
            # Create attributes
            attributes = self.create_kendra_attributes(tenant_id, metadata, document_type, doc_id)
            
            # Prepare document for Kendra
            kendra_document = {
                'Id': doc_id,
                'Title': title,
                'ContentType': content_type,
                'Attributes': attributes,
                'S3Path': {
                    'Bucket': bucket,
                    'Key': key
                }
            }
            
            # For S3-based ingestion, we don't provide the content directly
            # Kendra will fetch it from S3 using the S3Path
            # This applies to all content types
            
            # Ingest into Kendra
            logger.info(f"Ingesting document {doc_id} for tenant {tenant_id}")
            response = kendra.batch_put_document(
                IndexId=self.kendra_index_id,
                Documents=[kendra_document],
                RoleArn=os.environ.get('KENDRA_ROLE_ARN')  # Optional - only needed for S3 access
            ) if os.environ.get('KENDRA_ROLE_ARN') else kendra.batch_put_document(
                IndexId=self.kendra_index_id,
                Documents=[kendra_document]
            )
            
            # Check for failures
            if response.get('FailedDocuments'):
                logger.error(f"Failed to ingest document: {response['FailedDocuments']}")
                return {
                    'success': False,
                    'document_id': doc_id,
                    'error': response['FailedDocuments'][0].get('ErrorMessage', 'Unknown error')
                }
            
            # Update tracking table if available
            if self.doc_table:
                try:
                    self.doc_table.put_item(
                        Item={
                            'document_id': doc_id,
                            'tenant_id': tenant_id,
                            'document_type': document_type,
                            'title': title,
                            's3_bucket': bucket,
                            's3_key': key,
                            'ingested_at': datetime.utcnow().isoformat(),
                            'status': 'indexed'
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to update tracking table: {str(e)}")
            
            return {
                'success': True,
                'document_id': doc_id,
                'tenant_id': tenant_id,
                'document_type': document_type,
                'title': title
            }
            
        except Exception as e:
            logger.error(f"Error ingesting document {bucket}/{key}: {str(e)}")
            return {
                'success': False,
                'document_id': f"s3://{bucket}/{key}",
                'error': str(e)
            }
    
    def delete_document(self, bucket: str, key: str) -> Dict[str, Any]:
        """Delete a document from Kendra"""
        try:
            doc_id = self.generate_document_id(bucket, key)
            
            response = kendra.batch_delete_document(
                IndexId=self.kendra_index_id,
                DocumentIdList=[doc_id]
            )
            
            # Update tracking table if available
            if self.doc_table:
                try:
                    self.doc_table.update_item(
                        Key={'document_id': doc_id},
                        UpdateExpression='SET #status = :status, deleted_at = :deleted_at',
                        ExpressionAttributeNames={'#status': 'status'},
                        ExpressionAttributeValues={
                            ':status': 'deleted',
                            ':deleted_at': datetime.utcnow().isoformat()
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to update tracking table: {str(e)}")
            
            return {
                'success': True,
                'document_id': doc_id,
                'action': 'deleted'
            }
            
        except Exception as e:
            logger.error(f"Error deleting document {bucket}/{key}: {str(e)}")
            return {
                'success': False,
                'document_id': f"s3://{bucket}/{key}",
                'error': str(e)
            }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for custom Kendra ingestion"""
    logger.info(f"Processing event: {json.dumps(event)}")
    
    ingestor = KendraCustomIngestor()
    results = []
    
    # Process S3 events
    for record in event.get('Records', []):
        if record.get('eventSource') == 'aws:s3':
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            event_name = record['eventName']
            
            # Skip metadata files
            if key.endswith('.metadata.json') or '/metadata/' in key:
                logger.info(f"Skipping metadata file: {key}")
                continue
            
            # Process based on event type
            if event_name.startswith('ObjectCreated:'):
                result = ingestor.ingest_document(bucket, key)
                results.append(result)
            elif event_name.startswith('ObjectRemoved:'):
                result = ingestor.delete_document(bucket, key)
                results.append(result)
            else:
                logger.info(f"Ignoring event type: {event_name}")
    
    # Process direct invocation (for testing or manual ingestion)
    if 'bucket' in event and 'key' in event:
        action = event.get('action', 'ingest')
        if action == 'ingest':
            result = ingestor.ingest_document(event['bucket'], event['key'])
            results.append(result)
        elif action == 'delete':
            result = ingestor.delete_document(event['bucket'], event['key'])
            results.append(result)
    
    # Calculate summary
    successful = sum(1 for r in results if r.get('success', False))
    failed = len(results) - successful
    
    return {
        'statusCode': 200 if failed == 0 else 207,
        'body': json.dumps({
            'message': f'Processed {len(results)} documents',
            'successful': successful,
            'failed': failed,
            'results': results
        })
    }