#!/usr/bin/env python3
"""Test OpenSearch connectivity and indexing"""

import boto3
import json
import os
import requests
from requests_aws4auth import AWS4Auth

def test_opensearch():
    """Test OpenSearch connectivity and search"""
    
    # Get OpenSearch endpoint from Lambda environment or stack outputs
    try:
        lambda_client = boto3.client('lambda', region_name='ap-south-1')
        rag_functions = [f for f in lambda_client.list_functions()['Functions'] 
                        if 'RAGQueryFunction' in f['FunctionName']]
        
        if rag_functions:
            config = lambda_client.get_function_configuration(
                FunctionName=rag_functions[0]['FunctionName']
            )
            opensearch_endpoint = config['Environment']['Variables']['OPENSEARCH_ENDPOINT']
            print(f"OpenSearch endpoint: {opensearch_endpoint}")
        else:
            print("RAG Lambda function not found")
            return
            
    except Exception as e:
        print(f"Error getting OpenSearch endpoint: {e}")
        return
    
    # Setup AWS authentication
    region = 'ap-south-1'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        'es',
        session_token=credentials.token
    )
    
    # Test OpenSearch connectivity
    try:
        url = f"https://{opensearch_endpoint}/_cluster/health"
        response = requests.get(url, auth=awsauth, timeout=30)
        
        if response.status_code == 200:
            health = response.json()
            print(f"OpenSearch cluster status: {health.get('status', 'unknown')}")
            print(f"Number of nodes: {health.get('number_of_nodes', 0)}")
        else:
            print(f"OpenSearch health check failed: {response.status_code}")
            return
            
    except Exception as e:
        print(f"Error connecting to OpenSearch: {e}")
        return
    
    # Check indices
    try:
        url = f"https://{opensearch_endpoint}/_cat/indices?format=json"
        response = requests.get(url, auth=awsauth, timeout=30)
        
        if response.status_code == 200:
            indices = response.json()
            print(f"\nIndices found: {len(indices)}")
            
            for idx in indices:
                if 'strata' in idx.get('index', ''):
                    print(f"  - {idx['index']}: {idx.get('docs.count', 0)} documents")
        else:
            print(f"Failed to list indices: {response.status_code}")
            
    except Exception as e:
        print(f"Error listing indices: {e}")
        return
    
    # Test search on strata-documents index
    try:
        url = f"https://{opensearch_endpoint}/strata-documents/_search"
        search_body = {
            "query": {"match_all": {}},
            "size": 5,
            "_source": ["title", "document_id", "tenant_id"]
        }
        
        response = requests.post(
            url, 
            auth=awsauth, 
            headers={'Content-Type': 'application/json'},
            data=json.dumps(search_body),
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            total_docs = results['hits']['total']['value']
            print(f"\nTotal documents in strata-documents index: {total_docs}")
            
            if total_docs > 0:
                print("Sample documents:")
                for hit in results['hits']['hits']:
                    source = hit['_source']
                    print(f"  - {source.get('title', 'No title')} (tenant: {source.get('tenant_id', 'N/A')})")
            else:
                print("No documents found in index")
                
        elif response.status_code == 404:
            print("\nstrata-documents index does not exist")
        else:
            print(f"\nSearch failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error searching OpenSearch: {e}")

if __name__ == '__main__':
    test_opensearch()