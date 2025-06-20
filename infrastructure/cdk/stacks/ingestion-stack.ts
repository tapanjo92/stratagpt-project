import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import { Construct } from 'constructs';

export interface IngestionStackProps extends cdk.StackProps {
  documentBucket: s3.Bucket;
  openSearchDomain: opensearch.Domain;
}

export class IngestionStack extends cdk.Stack {
  public readonly textractLambda: lambda.Function;
  public readonly chunkSanitizerLambda: lambda.Function;
  public readonly embeddingsLambda: lambda.Function;
  public readonly ingestionStateMachine: sfn.StateMachine;

  constructor(scope: Construct, id: string, props: IngestionStackProps) {
    super(scope, id, props);

    const lambdaRole = new iam.Role(this, 'IngestionLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
      ]
    });

    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'textract:DetectDocumentText',
        'textract:AnalyzeDocument',
        'textract:StartDocumentTextDetection',
        'textract:GetDocumentTextDetection',
        'textract:StartDocumentAnalysis',
        'textract:GetDocumentAnalysis'
      ],
      resources: ['*']
    }));

    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream'
      ],
      resources: ['*']
    }));

    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:ListBucket'
      ],
      resources: [
        props.documentBucket.bucketArn,
        `${props.documentBucket.bucketArn}/*`
      ]
    }));

    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'es:ESHttpPost',
        'es:ESHttpPut',
        'es:ESHttpGet'
      ],
      resources: [`${props.openSearchDomain.domainArn}/*`]
    }));

    this.textractLambda = new lambda.Function(this, 'TextractProcessor', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import json
import boto3
import os
from typing import Dict, Any

textract = boto3.client('textract')
s3 = boto3.client('s3')

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    bucket = event['bucket']
    key = event['key']
    tenant_id = event['tenantId']
    document_id = event['documentId']
    
    try:
        response = textract.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            NotificationChannel={
                'RoleArn': os.environ['TEXTRACT_ROLE_ARN'],
                'SNSTopicArn': os.environ['TEXTRACT_SNS_TOPIC_ARN']
            }
        )
        
        return {
            'statusCode': 200,
            'jobId': response['JobId'],
            'tenantId': tenant_id,
            'documentId': document_id,
            'bucket': bucket,
            'key': key
        }
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        raise
`),
      role: lambdaRole,
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      environment: {
        'TEXTRACT_ROLE_ARN': lambdaRole.roleArn,
        'TEXTRACT_SNS_TOPIC_ARN': 'placeholder'
      }
    });

    this.chunkSanitizerLambda = new lambda.Function(this, 'ChunkSanitizer', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import json
import re
from typing import Dict, Any, List

def sanitize_pii(text: str) -> str:
    email_pattern = r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b'
    phone_pattern = r'\\b(?:\\+61|0)[2-478](?:[ -]?\\d){8}\\b'
    tfn_pattern = r'\\b\\d{3}[ -]?\\d{3}[ -]?\\d{3}\\b'
    
    text = re.sub(email_pattern, '[EMAIL_REDACTED]', text)
    text = re.sub(phone_pattern, '[PHONE_REDACTED]', text)
    text = re.sub(tfn_pattern, '[TFN_REDACTED]', text)
    
    return text

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
    
    return chunks

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    text = event['text']
    tenant_id = event['tenantId']
    document_id = event['documentId']
    
    sanitized_text = sanitize_pii(text)
    chunks = chunk_text(sanitized_text)
    
    return {
        'statusCode': 200,
        'tenantId': tenant_id,
        'documentId': document_id,
        'chunks': chunks,
        'totalChunks': len(chunks)
    }
`),
      role: lambdaRole,
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024
    });

    this.embeddingsLambda = new lambda.Function(this, 'EmbeddingsGenerator', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import json
import boto3
import os
from typing import Dict, Any, List
import urllib3
from urllib.parse import urlparse

bedrock = boto3.client('bedrock-runtime')
http = urllib3.PoolManager()

def generate_embeddings(text: str) -> List[float]:
    response = bedrock.invoke_model(
        modelId='amazon.titan-embed-text-v2:0',
        body=json.dumps({
            'inputText': text,
            'dimensions': 768,
            'normalize': True
        })
    )
    
    result = json.loads(response['body'].read())
    return result['embedding']

def index_to_opensearch(tenant_id: str, document_id: str, chunk_id: str, 
                       text: str, embedding: List[float]) -> None:
    opensearch_endpoint = os.environ['OPENSEARCH_ENDPOINT']
    index_name = f"strata-{tenant_id}"
    
    doc = {
        'tenant_id': tenant_id,
        'document_id': document_id,
        'chunk_id': chunk_id,
        'text': text,
        'embedding': embedding,
        'timestamp': datetime.now().isoformat()
    }
    
    url = f"https://{opensearch_endpoint}/{index_name}/_doc/{chunk_id}"
    headers = {'Content-Type': 'application/json'}
    
    response = http.request(
        'PUT',
        url,
        body=json.dumps(doc),
        headers=headers
    )
    
    if response.status != 200 and response.status != 201:
        raise Exception(f"Failed to index document: {response.data}")

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    chunks = event['chunks']
    tenant_id = event['tenantId']
    document_id = event['documentId']
    
    indexed_count = 0
    
    for i, chunk in enumerate(chunks):
        embedding = generate_embeddings(chunk)
        chunk_id = f"{document_id}_chunk_{i}"
        
        index_to_opensearch(
            tenant_id, document_id, chunk_id, chunk, embedding
        )
        
        indexed_count += 1
    
    return {
        'statusCode': 200,
        'tenantId': tenant_id,
        'documentId': document_id,
        'indexedChunks': indexed_count
    }
`),
      role: lambdaRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 2048,
      environment: {
        'OPENSEARCH_ENDPOINT': props.openSearchDomain.domainEndpoint
      }
    });

    const textractTask = new tasks.LambdaInvoke(this, 'TextractTask', {
      lambdaFunction: this.textractLambda,
      outputPath: '$.Payload'
    });

    const waitForTextract = new sfn.Wait(this, 'WaitForTextract', {
      time: sfn.WaitTime.duration(cdk.Duration.seconds(30))
    });

    const chunkTask = new tasks.LambdaInvoke(this, 'ChunkTask', {
      lambdaFunction: this.chunkSanitizerLambda,
      outputPath: '$.Payload'
    });

    const embeddingsTask = new tasks.LambdaInvoke(this, 'EmbeddingsTask', {
      lambdaFunction: this.embeddingsLambda,
      outputPath: '$.Payload'
    });

    const definition = textractTask
      .next(waitForTextract)
      .next(chunkTask)
      .next(embeddingsTask);

    this.ingestionStateMachine = new sfn.StateMachine(this, 'IngestionStateMachine', {
      definitionBody: sfn.DefinitionBody.fromChainable(definition),
      timeout: cdk.Duration.minutes(30),
      tracingEnabled: true
    });

    const ingestionRule = new events.Rule(this, 'IngestionRule', {
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
        detail: {
          bucket: {
            name: [props.documentBucket.bucketName]
          }
        }
      }
    });

    ingestionRule.addTarget(new targets.SfnStateMachine(this.ingestionStateMachine));

    new cdk.CfnOutput(this, 'StateMachineArn', {
      value: this.ingestionStateMachine.stateMachineArn,
      exportName: `${this.stackName}-StateMachineArn`
    });
  }
}