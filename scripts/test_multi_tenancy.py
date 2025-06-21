#!/usr/bin/env python3
"""
Test multi-tenant isolation in the RAG system
This verifies that tenants cannot access each other's data
"""
import boto3
import json
import sys

def test_tenant_isolation():
    """Test multi-tenant isolation in RAG system"""
    lambda_client = boto3.client('lambda', region_name='ap-south-1')
    
    # Find RAG function
    response = lambda_client.list_functions()
    rag_function = None
    for func in response['Functions']:
        if 'RAGQueryFunction' in func['FunctionName']:
            rag_function = func['FunctionName']
            break
    
    if not rag_function:
        print("Error: RAG function not found")
        return
    
    print(f"Using Lambda function: {rag_function}")
    
    # Test queries with different tenant IDs
    test_cases = [
        ("test-tenant", "Should return results"),
        ("tenant-a", "Should return NO results (isolation)"),
        ("tenant-b", "Should return NO results (isolation)"),  
        ("invalid-tenant", "Should return NO results (isolation)"),
        ("ALL", "Should return results (bypass for testing)")
    ]
    
    question = "What is the quorum for an AGM?"
    
    for tenant_id, expected in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing tenant_id: {tenant_id}")
        print(f"Expected: {expected}")
        print(f"{'='*60}")
        
        payload = {
            'question': question,
            'tenant_id': tenant_id,
            'max_results': 5
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName=rag_function,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            body = json.loads(result['body'])
            
            citations = body.get('citations', [])
            answer = body.get('answer', 'No answer')
            
            print(f"Citations found: {len(citations)}")
            print(f"Answer preview: {answer[:200]}...")
            
            # Check if isolation is working
            if tenant_id in ['tenant-a', 'tenant-b', 'invalid-tenant'] and len(citations) > 0:
                print("❌ SECURITY ISSUE: Tenant isolation not working!")
                print("   This tenant should NOT see any documents!")
                
                # Show which documents were wrongly returned
                for citation in citations:
                    print(f"   - Wrongly accessed: {citation.get('title', 'Unknown')}")
                    
            elif tenant_id in ['test-tenant', 'ALL'] and len(citations) == 0:
                print("⚠️  WARNING: Expected results but found none")
                print("   Check if documents are properly indexed")
            else:
                print("✅ Result matches expectation")
                
        except Exception as e:
            print(f"Error: {str(e)}")

    print(f"\n{'='*60}")
    print("MULTI-TENANT ISOLATION TEST COMPLETE")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_tenant_isolation()