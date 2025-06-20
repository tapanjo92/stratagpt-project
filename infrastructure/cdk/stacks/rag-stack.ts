import * as cdk from 'aws-cdk-lib';
import * as kendra from 'aws-cdk-lib/aws-kendra';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export interface RAGStackProps extends cdk.StackProps {
  documentBucket: s3.Bucket;
  openSearchDomain: opensearch.Domain;
}

export class RAGStack extends cdk.Stack {
  public readonly kendraIndex: kendra.CfnIndex;
  public readonly ragQueryLambda: lambda.Function;
  public readonly evaluationLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: RAGStackProps) {
    super(scope, id, props);

    // Create IAM role for Kendra
    const kendraRole = new iam.Role(this, 'KendraRole', {
      assumedBy: new iam.ServicePrincipal('kendra.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess')
      ]
    });

    // Grant Kendra access to S3 bucket
    props.documentBucket.grantRead(kendraRole);

    // Create Kendra Index
    this.kendraIndex = new kendra.CfnIndex(this, 'StrataKendraIndex', {
      name: 'strata-documents-index',
      roleArn: kendraRole.roleArn,
      edition: 'DEVELOPER_EDITION', // Use ENTERPRISE_EDITION for production
      description: 'Kendra index for Australian Strata documents',
      documentMetadataConfigurations: [
        {
          name: 'tenant_id',
          type: 'STRING_VALUE',
          search: {
            facetable: true,
            searchable: true,
            displayable: true
          }
        },
        {
          name: 'document_type',
          type: 'STRING_VALUE',
          search: {
            facetable: true,
            searchable: true,
            displayable: true
          }
        },
        {
          name: 'upload_date',
          type: 'DATE_VALUE',
          search: {
            facetable: true,
            searchable: false,
            displayable: true
          }
        }
      ],
      tags: [{
        key: 'Environment',
        value: 'dev'
      }]
    });

    // Create S3 data source for Kendra
    const dataSource = new kendra.CfnDataSource(this, 'S3DataSource', {
      indexId: this.kendraIndex.ref,
      name: 'strata-documents-datasource',
      type: 'S3',
      dataSourceConfiguration: {
        s3Configuration: {
          bucketName: props.documentBucket.bucketName,
          inclusionPrefixes: ['documents/'],
          documentsMetadataConfiguration: {
            s3Prefix: 'metadata/'
          }
        }
      },
      roleArn: kendraRole.roleArn,
      schedule: 'cron(0 * * * ? *)' // Sync every hour (at minute 0)
    });

    // Lambda role for RAG query
    const ragLambdaRole = new iam.Role(this, 'RAGLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess')
      ]
    });

    // Grant permissions for Kendra, Bedrock, and OpenSearch
    ragLambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'kendra:Query',
        'kendra:Retrieve',
        'kendra:BatchGetDocumentStatus'
      ],
      resources: [this.kendraIndex.attrArn]
    }));

    ragLambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream'
      ],
      resources: ['*']
    }));

    ragLambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'es:ESHttpPost',
        'es:ESHttpGet'
      ],
      resources: [`${props.openSearchDomain.domainArn}/*`]
    }));

    ragLambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        's3:GetObject'
      ],
      resources: [`${props.documentBucket.bucketArn}/*`]
    }));

    // Environment variables
    const ragEnvironment = {
      'KENDRA_INDEX_ID': this.kendraIndex.ref,
      'OPENSEARCH_ENDPOINT': props.openSearchDomain.domainEndpoint,
      'DOCUMENT_BUCKET': props.documentBucket.bucketName,
      'BEDROCK_MODEL_ID': 'anthropic.claude-3-opus-20240229-v1:0'
    };

    // RAG Query Lambda
    this.ragQueryLambda = new lambda.Function(this, 'RAGQueryFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('../../backend/lambdas/rag-query'),
      role: ragLambdaRole,
      timeout: cdk.Duration.seconds(30),
      memorySize: 2048,
      environment: ragEnvironment,
      tracing: lambda.Tracing.ACTIVE
    });

    // Create a separate role for evaluation Lambda to avoid circular dependency
    const evaluationLambdaRole = new iam.Role(this, 'EvaluationLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess')
      ]
    });

    // Grant permissions to invoke RAG Lambda
    evaluationLambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: ['lambda:InvokeFunction'],
      resources: [this.ragQueryLambda.functionArn]
    }));

    // Grant Bedrock access for evaluation
    evaluationLambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel'
      ],
      resources: ['*']
    }));

    // Evaluation Lambda for testing
    this.evaluationLambda = new lambda.Function(this, 'EvaluationFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('../../backend/lambdas/rag-evaluation'),
      role: evaluationLambdaRole,
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      environment: {
        'KENDRA_INDEX_ID': this.kendraIndex.ref,
        'BEDROCK_MODEL_ID': 'anthropic.claude-3-opus-20240229-v1:0',
        'RAG_LAMBDA_NAME': this.ragQueryLambda.functionName
      },
      tracing: lambda.Tracing.ACTIVE
    });

    // Store important values in SSM Parameter Store
    new ssm.StringParameter(this, 'KendraIndexIdParam', {
      parameterName: '/strata-gpt/kendra-index-id',
      stringValue: this.kendraIndex.ref
    });

    // Outputs
    new cdk.CfnOutput(this, 'KendraIndexId', {
      value: this.kendraIndex.ref,
      exportName: `${this.stackName}-KendraIndexId`
    });

    new cdk.CfnOutput(this, 'RAGLambdaArn', {
      value: this.ragQueryLambda.functionArn,
      exportName: `${this.stackName}-RAGLambdaArn`
    });

    new cdk.CfnOutput(this, 'EvaluationLambdaArn', {
      value: this.evaluationLambda.functionArn,
      exportName: `${this.stackName}-EvaluationLambdaArn`
    });
  }
}