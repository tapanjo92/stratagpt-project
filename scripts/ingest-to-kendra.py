#!/usr/bin/env python3
"""
Script to manually trigger Kendra ingestion for documents.
This is a temporary solution until we resolve the circular dependency issue.
"""

import boto3
import json
import sys
import argparse
from typing import List, Dict

def get_lambda_function_name():
    """Get the Kendra ingest Lambda function name from CloudFormation"""
    cf = boto3.client('cloudformation', region_name='ap-south-1')
    
    try:
        response = cf.describe_stacks(StackName='StrataGPT-RAG-dev')
        outputs = response['Stacks'][0]['Outputs']
        
        for output in outputs:
            if output['OutputKey'] == 'KendraIngestLambdaArn':
                # Extract function name from ARN
                arn = output['OutputValue']
                return arn.split(':')[-1]
                
    except Exception as e:
        print(f"Error getting Lambda function name: {e}")
        return None

def ingest_document(bucket: str, key: str, lambda_client) -> Dict:
    """Ingest a single document to Kendra"""
    
    function_name = get_lambda_function_name()
    if not function_name:
        function_name = 'StrataGPT-RAG-dev-KendraIngestFunction18D845D9-bcnnmaXv9Sr5'
        print(f"Using default function name: {function_name}")
    
    payload = {
        'bucket': bucket,
        'key': key,
        'action': 'ingest'
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        return result
        
    except Exception as e:
        return {'error': str(e)}

def list_documents(bucket: str, prefix: str, s3_client) -> List[str]:
    """List all documents in S3 with given prefix"""
    documents = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        for page in pages:
            for obj in page.get('Contents', []):
                key = obj['Key']
                # Skip metadata files and directories
                if not key.endswith('/') and '/metadata/' not in key:
                    documents.append(key)
                    
    except Exception as e:
        print(f"Error listing documents: {e}")
        
    return documents

def main():
    parser = argparse.ArgumentParser(description='Ingest documents to Kendra')
    parser.add_argument('--bucket', default='strata-documents-809555764832-ap-south-1',
                        help='S3 bucket name')
    parser.add_argument('--tenant', help='Tenant ID to process')
    parser.add_argument('--key', help='Specific document key to ingest')
    parser.add_argument('--all', action='store_true', 
                        help='Process all documents in bucket')
    parser.add_argument('--dry-run', action='store_true',
                        help='List documents without processing')
    
    args = parser.parse_args()
    
    # Initialize AWS clients
    s3_client = boto3.client('s3', region_name='ap-south-1')
    lambda_client = boto3.client('lambda', region_name='ap-south-1')
    
    documents_to_process = []
    
    if args.key:
        # Process specific document
        documents_to_process = [args.key]
    elif args.tenant:
        # Process all documents for a tenant
        prefix = f"{args.tenant}/documents/"
        documents_to_process = list_documents(args.bucket, prefix, s3_client)
    elif args.all:
        # Process all documents
        documents_to_process = list_documents(args.bucket, "", s3_client)
    else:
        print("Please specify --key, --tenant, or --all")
        sys.exit(1)
    
    print(f"Found {len(documents_to_process)} documents to process")
    
    if args.dry_run:
        print("\nDocuments that would be processed:")
        for doc in documents_to_process:
            print(f"  - {doc}")
        return
    
    # Process documents
    successful = 0
    failed = 0
    
    for i, key in enumerate(documents_to_process):
        print(f"\nProcessing {i+1}/{len(documents_to_process)}: {key}")
        
        result = ingest_document(args.bucket, key, lambda_client)
        
        if 'statusCode' in result and result['statusCode'] == 200:
            body = json.loads(result['body'])
            if body['successful'] > 0:
                successful += 1
                print(f"  ✓ Successfully ingested")
            else:
                failed += 1
                print(f"  ✗ Failed: {body['results'][0].get('error', 'Unknown error')}")
        else:
            failed += 1
            print(f"  ✗ Error: {result.get('error', 'Unknown error')}")
    
    print(f"\n\nSummary:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(documents_to_process)}")

if __name__ == '__main__':
    main()