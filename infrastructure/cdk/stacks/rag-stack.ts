import * as cdk from 'aws-cdk-lib';
import * as kendra from 'aws-cdk-lib/aws-kendra';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export interface RAGStackProps extends cdk.StackProps {
  documentBucket: s3.Bucket;
  openSearchDomain: opensearch.Domain;
}

export class RAGStack extends cdk.Stack {
  public readonly kendraIndex: kendra.CfnIndex;
  public readonly kendraIndexId: string;
  public readonly ragQueryLambda: lambda.Function;
  public readonly ragQueryFunction: lambda.Function;
  public readonly evaluationLambda: lambda.Function;
  public readonly kendraIngestLambda: lambda.Function;
  public readonly documentTrackingTable: dynamodb.Table;

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
    
    // Store the Kendra index ID for other stacks
    this.kendraIndexId = this.kendraIndex.ref;

    // NOTE: We're keeping the S3 data source for backward compatibility
    // but new documents will be ingested using the custom Lambda
    const dataSource = new kendra.CfnDataSource(this, 'S3DataSource', {
      indexId: this.kendraIndex.ref,
      name: 'strata-documents-datasource',
      type: 'S3',
      dataSourceConfiguration: {
        s3Configuration: {
          bucketName: props.documentBucket.bucketName,
          inclusionPrefixes: ['test-tenant/documents/'],
          documentsMetadataConfiguration: {
            s3Prefix: 'test-tenant/metadata/'
          }
        }
      },
      roleArn: kendraRole.roleArn,
      schedule: 'cron(0 * * * ? *)' // Sync every hour (at minute 0)
    });

    // Create DynamoDB table for document tracking
    this.documentTrackingTable = new dynamodb.Table(this, 'DocumentTrackingTable', {
      tableName: 'strata-documents',
      partitionKey: { name: 'document_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true
    });

    // Add GSI for tenant queries
    this.documentTrackingTable.addGlobalSecondaryIndex({
      indexName: 'tenant-index',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'ingested_at', type: dynamodb.AttributeType.STRING }
    });

    // Create IAM role for custom Kendra ingestion Lambda
    const kendraIngestRole = new iam.Role(this, 'KendraIngestLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess')
      ]
    });

    // Grant permissions for Kendra ingestion
    kendraIngestRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'kendra:BatchPutDocument',
        'kendra:BatchDeleteDocument'
      ],
      resources: [this.kendraIndex.attrArn]
    }));

    // Grant permission to pass the Kendra role
    kendraIngestRole.addToPolicy(new iam.PolicyStatement({
      actions: ['iam:PassRole'],
      resources: [kendraRole.roleArn],
      conditions: {
        StringEquals: {
          'iam:PassedToService': 'kendra.amazonaws.com'
        }
      }
    }));

    // Grant S3 permissions
    props.documentBucket.grantRead(kendraIngestRole);
    kendraIngestRole.addToPolicy(new iam.PolicyStatement({
      actions: ['s3:GetObjectTagging'],
      resources: [`${props.documentBucket.bucketArn}/*`]
    }));

    // Grant DynamoDB permissions
    this.documentTrackingTable.grantReadWriteData(kendraIngestRole);

    // Custom Kendra Ingestion Lambda
    this.kendraIngestLambda = new lambda.Function(this, 'KendraIngestFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('../../backend/lambdas/kendra-custom-ingest'),
      role: kendraIngestRole,
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      environment: {
        'KENDRA_INDEX_ID': this.kendraIndex.ref,
        'DOCUMENT_TABLE': this.documentTrackingTable.tableName,
        'KENDRA_ROLE_ARN': kendraRole.roleArn
      },
      tracing: lambda.Tracing.ACTIVE
    });

    // NOTE: S3 event notifications would create a circular dependency
    // For now, documents will be ingested by invoking the Lambda directly
    // or through a separate trigger mechanism

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
      'BEDROCK_MODEL_ID': 'anthropic.claude-sonnet-4-20250514-v1:0',
      'USE_OPENSEARCH': 'true',  // Switch to OpenSearch for better tenant filtering
      // Using Claude Sonnet 4 - latest model available in ap-south-1
    };

    // RAG Query Lambda
    this.ragQueryLambda = new lambda.Function(this, 'RAGQueryFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('../../backend/lambdas/rag-query'),
      role: ragLambdaRole,
      timeout: cdk.Duration.seconds(60),
      memorySize: 2048,
      environment: ragEnvironment,
      tracing: lambda.Tracing.ACTIVE
    });
    
    // Also expose as ragQueryFunction for consistency
    this.ragQueryFunction = this.ragQueryLambda;

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
      timeout: cdk.Duration.minutes(10),
      memorySize: 1024,
      reservedConcurrentExecutions: 1, // Prevent concurrent executions to avoid Kendra throttling
      environment: {
        'KENDRA_INDEX_ID': this.kendraIndex.ref,
        'BEDROCK_MODEL_ID': 'anthropic.claude-sonnet-4-20250514-v1:0',
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

    new cdk.CfnOutput(this, 'KendraIngestLambdaArn', {
      value: this.kendraIngestLambda.functionArn,
      exportName: `${this.stackName}-KendraIngestLambdaArn`
    });

    new cdk.CfnOutput(this, 'DocumentTrackingTableName', {
      value: this.documentTrackingTable.tableName,
      exportName: `${this.stackName}-DocumentTrackingTableName`
    });
  }
}