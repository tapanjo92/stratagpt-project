import json
import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
kendra = boto3.client('kendra')

def handler(event, context):
    """
    Lambda function to create Kendra-compatible metadata files when documents are uploaded.
    This ensures proper document indexing with metadata attributes.
    """
    
    kendra_index_id = os.environ['KENDRA_INDEX_ID']
    
    for record in event.get('Records', []):
        # Process S3 events
        if record.get('eventSource') == 'aws:s3':
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            # Skip if this is already a metadata file
            if key.endswith('.metadata.json'):
                continue
                
            # Parse the S3 key to extract tenant_id
            # Expected format: tenant-id/documents/filename.ext
            key_parts = key.split('/')
            if len(key_parts) < 3 or key_parts[1] != 'documents':
                logger.warning(f"Skipping file with unexpected path format: {key}")
                continue
                
            tenant_id = key_parts[0]
            filename = key_parts[-1]
            
            try:
                # Get the object metadata
                response = s3.head_object(Bucket=bucket, Key=key)
                s3_metadata = response.get('Metadata', {})
                
                # Create Kendra metadata
                kendra_metadata = {
                    "DocumentId": key,
                    "Attributes": {
                        "tenant_id": s3_metadata.get('tenant_id', tenant_id),
                        "document_type": s3_metadata.get('document_type', 'general'),
                        "_category": s3_metadata.get('document_type', 'general'),
                        "_created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "_source_uri": f"s3://{bucket}/{key}"
                    }
                }
                
                # Add title if available
                if 'title' in s3_metadata:
                    kendra_metadata["Title"] = s3_metadata['title']
                
                # Create metadata file path
                # Kendra expects: tenant-id/metadata/filename.ext.metadata.json
                metadata_key = f"{tenant_id}/metadata/{filename}.metadata.json"
                
                # Upload metadata file
                s3.put_object(
                    Bucket=bucket,
                    Key=metadata_key,
                    Body=json.dumps(kendra_metadata, indent=2),
                    ContentType='application/json'
                )
                
                logger.info(f"Created Kendra metadata file: {metadata_key}")
                
            except Exception as e:
                logger.error(f"Error creating metadata for {key}: {str(e)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Metadata files created successfully')
    }