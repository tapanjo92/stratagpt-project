# Kendra Metadata Indexing Solution

## Problem Summary
The Kendra S3 data source is not properly associating metadata files with documents, preventing tenant_id filtering from working correctly. While the Kendra index is properly configured and the filtering code works, the S3 data source has limitations in how it processes metadata files.

## Root Cause
1. **S3 Data Source Limitations**: Kendra's S3 data source has specific requirements for metadata files that are not well documented
2. **Timing Issues**: Metadata files must exist before documents are indexed
3. **Path Structure**: The current implementation may not match Kendra's expected structure

## Verified Working Solution
Direct document ingestion using `batch_put_document` API works perfectly with tenant filtering. This confirms:
- ✅ Kendra index configuration is correct
- ✅ Tenant filtering code is correct
- ✅ Attribute schema is properly defined

## Recommended Solutions

### Option 1: Custom Document Ingestion (Recommended)
Instead of relying on S3 data source sync, implement a custom ingestion pipeline:

```python
# In the document processing Lambda
def ingest_to_kendra(document_content, s3_key, tenant_id, metadata):
    kendra = boto3.client('kendra')
    
    response = kendra.batch_put_document(
        IndexId=KENDRA_INDEX_ID,
        Documents=[{
            'Id': s3_key,
            'Title': metadata.get('title', 'Untitled'),
            'ContentType': 'PLAIN_TEXT',
            'Blob': document_content.encode('utf-8'),
            'Attributes': [
                {'Key': 'tenant_id', 'Value': {'StringValue': tenant_id}},
                {'Key': 'document_type', 'Value': {'StringValue': metadata.get('document_type', 'general')}},
                {'Key': '_source_uri', 'Value': {'StringValue': f's3://{BUCKET}/{s3_key}'}}
            ],
            'S3Path': {
                'Bucket': BUCKET,
                'Key': s3_key
            }
        }]
    )
    return response
```

**Advantages:**
- Full control over metadata
- Immediate indexing
- No sync delays
- Guaranteed tenant isolation

**Implementation Steps:**
1. Modify the document processing pipeline to call `batch_put_document`
2. Remove dependency on S3 data source sync
3. Handle document updates and deletions explicitly

### Option 2: Switch to OpenSearch
The code already has OpenSearch support partially implemented. Complete the migration:

**Advantages:**
- Better control over document structure
- More flexible querying
- Native tenant filtering support
- Lower cost than Kendra

**Implementation Steps:**
1. Enable OpenSearch client in RAG handler
2. Index documents with tenant_id field
3. Use OpenSearch query with tenant filter

### Option 3: Pre-process Documents for S3 Sync
Create a more robust metadata handling system:

1. Upload metadata files first, wait for confirmation
2. Then upload documents
3. Use Lambda to orchestrate the correct order
4. Add retry logic for failed associations

## Immediate Workaround
For testing and development, continue using `tenant_id='ALL'` to bypass filtering. This allows full functionality while a permanent solution is implemented.

## Recommended Action Plan

1. **Short-term (1-2 days)**
   - Continue using tenant_id='ALL' for development
   - Document the limitation for other developers
   - Begin implementing Option 1 (custom ingestion)

2. **Medium-term (1 week)**
   - Complete custom ingestion implementation
   - Test with multiple tenants
   - Update documentation

3. **Long-term (2-4 weeks)**
   - Evaluate OpenSearch migration for cost savings
   - Implement full multi-tenant support
   - Performance optimization

## Cost Implications
- Current Kendra Developer Edition: $810/month
- Custom ingestion: Same cost, better functionality
- OpenSearch option: ~$50-100/month (significant savings)

## Security Considerations
- Tenant isolation is enforced at query time (working)
- Document-level security requires proper metadata (currently not working with S3 sync)
- Custom ingestion ensures security from the start

## Conclusion
While Kendra's S3 data source has limitations with metadata, the core functionality is sound. Implementing custom document ingestion will provide full tenant isolation support without changing the query interface.