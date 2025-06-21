# Custom Kendra Ingestion Implementation

## Overview
Successfully implemented a custom document ingestion solution using Kendra's `batch_put_document` API to ensure proper tenant isolation through metadata attributes.

## Implementation Details

### Architecture Changes
1. **New Lambda Function**: `kendra-custom-ingest`
   - Handles document ingestion directly to Kendra
   - Extracts tenant_id from S3 path structure
   - Adds metadata attributes during ingestion
   - Tracks documents in DynamoDB table

2. **DynamoDB Table**: `strata-documents`
   - Tracks all indexed documents
   - Enables querying by tenant_id
   - Stores indexing status and metadata

3. **Infrastructure Updates**:
   - Added custom ingestion Lambda to RAG stack
   - Created document tracking table with GSI
   - Configured proper IAM permissions

### Key Components

#### Lambda Function Features
- Automatic tenant_id extraction from S3 path
- Document type inference from filename
- Metadata extraction from S3 object tags
- Support for multiple content types (TXT, PDF, DOCX, HTML)
- Document tracking in DynamoDB
- Error handling and retry logic

#### Security Implementation
- IAM PassRole permission for Kendra role
- S3 read permissions scoped to document bucket
- DynamoDB read/write for tracking table
- Proper tenant isolation enforced

## Testing Results

### Successful Multi-Tenant Testing
1. **Document Ingestion**:
   - ✅ Tenant-a document successfully indexed
   - ✅ Tenant-b document successfully indexed
   - ✅ Metadata attributes properly associated

2. **Tenant Isolation Verification**:
   - ✅ Tenant-a can only query their documents
   - ✅ Tenant-b can only query their documents
   - ✅ Cross-tenant queries return no results
   - ✅ AttributeFilter working correctly

3. **Performance**:
   - Document ingestion: ~1-2 seconds
   - Query response time: 2-3 seconds
   - Proper citation tracking

## Usage Guide

### Manual Document Ingestion
```bash
# Invoke the Lambda directly
aws lambda invoke \
  --function-name StrataGPT-RAG-dev-KendraIngestFunction18D845D9-bcnnmaXv9Sr5 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"bucket": "strata-documents-809555764832-ap-south-1", "key": "tenant-id/documents/filename.txt", "action": "ingest"}' \
  result.json
```

### Document Structure
Documents should be uploaded to S3 with the following path structure:
```
s3://bucket-name/tenant-id/documents/filename.ext
```

### Metadata Support
Add metadata to S3 objects for better categorization:
```bash
aws s3 cp document.pdf s3://bucket/tenant-id/documents/ \
  --metadata tenant_id=tenant-id,document_type=bylaws,title="Building By-laws"
```

## Future Enhancements

1. **Automatic Triggers**:
   - Add S3 event notifications (requires resolving circular dependency)
   - Use EventBridge for decoupled architecture

2. **Batch Processing**:
   - Support bulk document ingestion
   - Progress tracking for large uploads

3. **Enhanced Metadata**:
   - Extract metadata from document content
   - Auto-categorization using ML

4. **Monitoring**:
   - CloudWatch metrics for ingestion success/failure
   - Alerts for failed ingestions

## Migration from S3 Data Source

To migrate existing documents from S3 data source to custom ingestion:

1. List all documents in S3
2. For each document, invoke the custom ingestion Lambda
3. Verify documents are indexed with proper metadata
4. Disable or remove the S3 data source

## Cost Optimization

- Custom ingestion eliminates the need for S3 data source sync
- More efficient than hourly sync schedules
- Pay only for actual document processing
- Consider batch operations for bulk uploads

## Conclusion

The custom ingestion implementation successfully solves the tenant isolation issue while providing better control over document metadata. This approach ensures security, scalability, and proper multi-tenant support for the Australian Strata GPT system.