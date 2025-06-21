#!/usr/bin/env python3
"""
Re-index all documents in S3 to Kendra with proper tenant_id attributes
This fixes the multi-tenant isolation issue
"""

import boto3
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize AWS clients
s3 = boto3.client('s3', region_name='ap-south-1')
lambda_client = boto3.client('lambda', region_name='ap-south-1')

# Configuration
BUCKET_NAME = 'strata-documents-809555764832-ap-south-1'
KENDRA_INGEST_FUNCTION = 'StrataGPT-RAG-dev-KendraIngestFunction18D845D9-bcnnmaXv9Sr5'

def get_all_documents():
    """Get all document keys from S3 bucket"""
    documents = []
    paginator = s3.get_paginator('list_objects_v2')
    
    for page in paginator.paginate(Bucket=BUCKET_NAME):
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                # Skip metadata files and only process documents
                if ('/documents/' in key and 
                    not key.endswith('.metadata.json') and
                    (key.endswith('.txt') or key.endswith('.pdf') or 
                     key.endswith('.docx') or key.endswith('.html'))):
                    documents.append(key)
    
    return documents

def ingest_document(key):
    """Ingest a single document using the Kendra custom ingest Lambda"""
    try:
        payload = {
            'bucket': BUCKET_NAME,
            'key': key,
            'action': 'ingest'
        }
        
        response = lambda_client.invoke(
            FunctionName=KENDRA_INGEST_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        status = 'SUCCESS' if response['StatusCode'] == 200 else 'FAILED'
        
        return {
            'key': key,
            'status': status,
            'result': result
        }
    except Exception as e:
        return {
            'key': key,
            'status': 'ERROR',
            'error': str(e)
        }

def main():
    print("Starting document re-indexing process...")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Lambda: {KENDRA_INGEST_FUNCTION}")
    
    # Get all documents
    documents = get_all_documents()
    print(f"\nFound {len(documents)} documents to re-index")
    
    # Group by tenant
    tenant_docs = {}
    for doc in documents:
        tenant_id = doc.split('/')[0]
        if tenant_id not in tenant_docs:
            tenant_docs[tenant_id] = []
        tenant_docs[tenant_id].append(doc)
    
    print("\nDocuments by tenant:")
    for tenant, docs in tenant_docs.items():
        print(f"  {tenant}: {len(docs)} documents")
    
    # Confirm before proceeding
    response = input("\nProceed with re-indexing? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    # Process documents with thread pool for parallelism
    successful = 0
    failed = 0
    errors = []
    
    print("\nRe-indexing documents...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(ingest_document, doc): doc for doc in documents}
        
        for future in as_completed(futures):
            result = future.result()
            if result['status'] == 'SUCCESS':
                successful += 1
                print(f"✅ {result['key']}")
            else:
                failed += 1
                errors.append(result)
                print(f"❌ {result['key']} - {result.get('error', 'Unknown error')}")
            
            # Rate limiting - avoid overwhelming Lambda
            time.sleep(0.2)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Re-indexing complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {len(documents)}")
    
    if errors:
        print(f"\nFailed documents:")
        for error in errors:
            print(f"  - {error['key']}: {error.get('error', 'Unknown')}")
    
    print("\nNOTE: It may take a few minutes for Kendra to fully index the documents.")
    print("Test multi-tenant isolation after 5 minutes.")

if __name__ == "__main__":
    main()