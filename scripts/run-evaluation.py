#!/usr/bin/env python3
"""
Run the evaluation harness for the Strata RAG system.
This script invokes the evaluation Lambda function to test the RAG system performance.
"""

import boto3
import json
import sys
import argparse
from datetime import datetime

def get_lambda_function_name(region='ap-south-1'):
    """Get the evaluation Lambda function name"""
    lambda_client = boto3.client('lambda', region_name=region)
    
    # List all functions and find the evaluation function
    response = lambda_client.list_functions()
    for func in response['Functions']:
        if 'EvaluationFunction' in func['FunctionName']:
            return func['FunctionName']
    
    raise Exception("Evaluation Lambda function not found")

def run_evaluation(region='ap-south-1', test_subset=None):
    """Run the evaluation harness"""
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Get function name
    function_name = get_lambda_function_name(region)
    print(f"Using Lambda function: {function_name}")
    
    # Prepare payload
    payload = {}
    if test_subset:
        payload['test_subset'] = test_subset
    
    print(f"Starting evaluation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("This may take several minutes to complete...")
    
    # Invoke Lambda
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    # Parse response
    result = json.loads(response['Payload'].read())
    
    if response['StatusCode'] == 200:
        body = json.loads(result.get('body', '{}'))
        summary = body.get('summary', {})
        
        print("\n" + "="*60)
        print("EVALUATION RESULTS")
        print("="*60)
        print(f"Total Questions: {summary.get('total_questions', 0)}")
        print(f"Passed: {summary.get('passed', 0)}")
        print(f"Failed: {summary.get('failed', 0)}")
        print(f"Pass Rate: {summary.get('pass_rate', 0):.1%}")
        print(f"Average Accuracy: {summary.get('average_accuracy', 0):.2f}")
        print(f"Average Response Time: {summary.get('average_response_time_ms', 0)}ms")
        
        # Show category breakdown if available
        if 'category_performance' in summary:
            print("\nPerformance by Category:")
            for category, performance in summary['category_performance'].items():
                print(f"  {category}: {performance.get('accuracy', 0):.1%} accuracy")
        
        # Save detailed results
        output_file = f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(body, f, indent=2)
        print(f"\nDetailed results saved to: {output_file}")
        
    else:
        print(f"Error: Lambda invocation failed with status {response['StatusCode']}")
        print(result)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Run Strata RAG evaluation')
    parser.add_argument('--region', default='ap-south-1', help='AWS region')
    parser.add_argument('--subset', choices=['easy', 'medium', 'hard'], 
                        help='Run only a subset of tests by difficulty')
    
    args = parser.parse_args()
    
    try:
        run_evaluation(region=args.region, test_subset=args.subset)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()