import json
import boto3
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger()
logger.setLevel(logging.INFO)

textract = boto3.client('textract')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

class DocumentType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    TIFF = "tiff"
    PNG = "png"
    JPEG = "jpeg"

@dataclass
class TextractRequest:
    bucket: str
    key: str
    tenant_id: str
    document_id: str
    document_type: DocumentType

class TextractProcessor:
    def __init__(self):
        self.metadata_table = dynamodb.Table(os.environ.get('METADATA_TABLE_NAME', 'strata-document-metadata'))
    
    def detect_document_type(self, key: str) -> DocumentType:
        ext = key.lower().split('.')[-1]
        mapping = {
            'pdf': DocumentType.PDF,
            'docx': DocumentType.DOCX,
            'tiff': DocumentType.TIFF,
            'tif': DocumentType.TIFF,
            'png': DocumentType.PNG,
            'jpg': DocumentType.JPEG,
            'jpeg': DocumentType.JPEG
        }
        return mapping.get(ext, DocumentType.PDF)
    
    def start_text_detection(self, request: TextractRequest) -> Dict[str, Any]:
        try:
            if request.document_type == DocumentType.PDF:
                response = textract.start_document_text_detection(
                    DocumentLocation={
                        'S3Object': {
                            'Bucket': request.bucket,
                            'Name': request.key
                        }
                    },
                    JobTag=f"{request.tenant_id}_{request.document_id}"
                )
                job_id = response['JobId']
                detection_type = 'async'
            else:
                response = textract.detect_document_text(
                    Document={
                        'S3Object': {
                            'Bucket': request.bucket,
                            'Name': request.key
                        }
                    }
                )
                job_id = None
                detection_type = 'sync'
                text = self.extract_text_from_response(response)
                
            self.update_metadata(request, job_id, detection_type)
            
            if detection_type == 'sync':
                return {
                    'statusCode': 200,
                    'jobId': job_id,
                    'tenantId': request.tenant_id,
                    'documentId': request.document_id,
                    'bucket': request.bucket,
                    'key': request.key,
                    'text': text,
                    'detectionType': detection_type
                }
            else:
                return {
                    'statusCode': 200,
                    'jobId': job_id,
                    'tenantId': request.tenant_id,
                    'documentId': request.document_id,
                    'bucket': request.bucket,
                    'key': request.key,
                    'detectionType': detection_type
                }
                
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise
    
    def extract_text_from_response(self, response: Dict[str, Any]) -> str:
        blocks = response.get('Blocks', [])
        text_lines = []
        
        for block in blocks:
            if block['BlockType'] == 'LINE':
                text_lines.append(block.get('Text', ''))
        
        return '\n'.join(text_lines)
    
    def update_metadata(self, request: TextractRequest, job_id: Optional[str], detection_type: str):
        try:
            self.metadata_table.update_item(
                Key={
                    'tenantId': request.tenant_id,
                    'documentId': request.document_id
                },
                UpdateExpression='SET textractJobId = :job_id, textractStatus = :status, detectionType = :type',
                ExpressionAttributeValues={
                    ':job_id': job_id or 'N/A',
                    ':status': 'processing',
                    ':type': detection_type
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update metadata: {str(e)}")

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"Received event: {json.dumps(event)}")
    
    processor = TextractProcessor()
    
    request = TextractRequest(
        bucket=event['bucket'],
        key=event['key'],
        tenant_id=event['tenantId'],
        document_id=event['documentId'],
        document_type=processor.detect_document_type(event['key'])
    )
    
    return processor.start_text_detection(request)