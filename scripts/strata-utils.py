#!/usr/bin/env python3
"""
Utility script for common Strata GPT operations
"""

import boto3
import json
import argparse
import sys
from datetime import datetime

class StrataUtils:
    def __init__(self, region='ap-south-1'):
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.ssm_client = boto3.client('ssm', region_name=region)
        self.kendra_client = boto3.client('kendra', region_name=region)
        
    def get_rag_lambda_name(self):
        """Get the RAG Lambda function name"""
        response = self.lambda_client.list_functions()
        for func in response['Functions']:
            if 'RAGQueryFunction' in func['FunctionName']:
                return func['FunctionName']
        raise Exception("RAG Lambda function not found")
    
    def query_rag(self, question, tenant_id='test-tenant'):
        """Query the RAG system"""
        function_name = self.get_rag_lambda_name()
        
        payload = {
            'question': question,
            'tenant_id': tenant_id,
            'max_results': 10,
            'answer_style': 'professional'
        }
        
        print(f"Querying: {question}")
        response = self.lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        body = json.loads(result['body'])
        
        print("\nAnswer:")
        print("-" * 60)
        print(body.get('answer', 'No answer available'))
        print("-" * 60)
        print(f"Citations: {len(body.get('citations', []))}")
        print(f"Response time: {body.get('processing_time_ms', 0)}ms")
        
        return body
    
    def check_kendra_status(self):
        """Check Kendra index and data source status"""
        try:
            # Get Kendra index ID from SSM
            response = self.ssm_client.get_parameter(Name='/strata-gpt/kendra-index-id')
            index_id = response['Parameter']['Value']
            
            # Get index status
            index_response = self.kendra_client.describe_index(Id=index_id)
            print(f"Kendra Index Status: {index_response['Status']}")
            
            # Get data source status
            ds_response = self.kendra_client.list_data_sources(IndexId=index_id)
            for ds in ds_response['SummaryItems']:
                print(f"Data Source '{ds['Name']}': {ds['Status']}")
                
                # Get recent sync jobs
                sync_response = self.kendra_client.list_data_source_sync_jobs(
                    Id=ds['Id'],
                    IndexId=index_id,
                    MaxResults=1
                )
                
                if sync_response['History']:
                    latest = sync_response['History'][0]
                    print(f"  Last sync: {latest['Status']} at {latest.get('StartTime', 'N/A')}")
                    if 'Metrics' in latest:
                        metrics = latest['Metrics']
                        print(f"  Documents: Added={metrics.get('DocumentsAdded', 0)}, "
                              f"Modified={metrics.get('DocumentsModified', 0)}, "
                              f"Failed={metrics.get('DocumentsFailed', 0)}")
        
        except Exception as e:
            print(f"Error checking Kendra status: {str(e)}")
    
    def list_stack_outputs(self, stack_name='StrataGPT-RAG-dev'):
        """List CloudFormation stack outputs"""
        cf_client = boto3.client('cloudformation', region_name=self.region)
        
        try:
            response = cf_client.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            
            print(f"Stack: {stack_name}")
            print(f"Status: {stack['StackStatus']}")
            print("\nOutputs:")
            
            for output in stack.get('Outputs', []):
                print(f"  {output['OutputKey']}: {output['OutputValue']}")
                
        except Exception as e:
            print(f"Error getting stack outputs: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Strata GPT Utilities')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query the RAG system')
    query_parser.add_argument('question', help='Question to ask')
    query_parser.add_argument('--tenant', default='test-tenant', help='Tenant ID (default: test-tenant)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check system status')
    
    # Outputs command
    outputs_parser = subparsers.add_parser('outputs', help='List stack outputs')
    outputs_parser.add_argument('--stack', default='StrataGPT-RAG-dev', help='Stack name')
    
    parser.add_argument('--region', default='ap-south-1', help='AWS region')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    utils = StrataUtils(region=args.region)
    
    try:
        if args.command == 'query':
            utils.query_rag(args.question, args.tenant)
        elif args.command == 'status':
            utils.check_kendra_status()
        elif args.command == 'outputs':
            utils.list_stack_outputs(args.stack)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()