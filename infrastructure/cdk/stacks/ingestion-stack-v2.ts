import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as logs from 'aws-cdk-lib/aws-logs';
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
  public readonly dlq: sqs.Queue;

  constructor(scope: Construct, id: string, props: IngestionStackProps) {
    super(scope, id, props);

    // Dead Letter Queue for failed messages
    this.dlq = new sqs.Queue(this, 'IngestionDLQ', {
      queueName: 'strata-ingestion-dlq',
      retentionPeriod: cdk.Duration.days(14),
      encryption: sqs.QueueEncryption.KMS_MANAGED
    });

    const lambdaRole = new iam.Role(this, 'IngestionLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess')
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

    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'cloudwatch:PutMetricData'
      ],
      resources: ['*']
    }));

    // Lambda environment variables
    const lambdaEnvironment = {
      'OPENSEARCH_ENDPOINT': props.openSearchDomain.domainEndpoint,
      'DOCUMENT_BUCKET': props.documentBucket.bucketName,
      'AWS_XRAY_TRACING_NAME': 'StrataIngestion',
      'POWERTOOLS_SERVICE_NAME': 'ingestion',
      'POWERTOOLS_METRICS_NAMESPACE': 'StrataGPT/Ingestion'
    };

    this.textractLambda = new lambda.Function(this, 'TextractProcessor', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('../backend/lambdas/textract-processor'),
      role: lambdaRole,
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      environment: lambdaEnvironment,
      tracing: lambda.Tracing.ACTIVE,
      retryAttempts: 2,
      deadLetterQueue: this.dlq,
      logRetention: logs.RetentionDays.ONE_YEAR
    });

    this.chunkSanitizerLambda = new lambda.Function(this, 'ChunkSanitizer', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('../backend/lambdas/chunk-sanitizer'),
      role: lambdaRole,
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      environment: lambdaEnvironment,
      tracing: lambda.Tracing.ACTIVE,
      retryAttempts: 2,
      deadLetterQueue: this.dlq,
      logRetention: logs.RetentionDays.ONE_YEAR
    });

    this.embeddingsLambda = new lambda.Function(this, 'EmbeddingsGenerator', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('../backend/lambdas/embeddings-generator'),
      role: lambdaRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 2048,
      environment: lambdaEnvironment,
      tracing: lambda.Tracing.ACTIVE,
      retryAttempts: 2,
      deadLetterQueue: this.dlq,
      logRetention: logs.RetentionDays.ONE_YEAR,
      reservedConcurrentExecutions: 10 // Throttle to avoid Bedrock rate limits
    });

    // Step Functions tasks with error handling
    const textractTask = new tasks.LambdaInvoke(this, 'TextractTask', {
      lambdaFunction: this.textractLambda,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
      resultPath: '$.textractResult'
    });

    const waitForTextract = new sfn.Wait(this, 'WaitForTextract', {
      time: sfn.WaitTime.duration(cdk.Duration.seconds(30))
    });

    const chunkTask = new tasks.LambdaInvoke(this, 'ChunkTask', {
      lambdaFunction: this.chunkSanitizerLambda,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
      resultPath: '$.chunkResult'
    });

    const embeddingsTask = new tasks.LambdaInvoke(this, 'EmbeddingsTask', {
      lambdaFunction: this.embeddingsLambda,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
      resultPath: '$.embeddingResult'
    });

    // Error handling states
    const handleError = new sfn.Fail(this, 'HandleError', {
      comment: 'Document processing failed'
    });

    const notifyError = new tasks.SqsSendMessage(this, 'NotifyError', {
      queue: this.dlq,
      messageBody: sfn.TaskInput.fromJsonPathAt('$')
    });

    // Add retry configuration to each task
    textractTask.addRetry({
      errors: ['States.TaskFailed'],
      interval: cdk.Duration.seconds(2),
      maxAttempts: 3,
      backoffRate: 2
    });

    chunkTask.addRetry({
      errors: ['States.TaskFailed'],
      interval: cdk.Duration.seconds(2),
      maxAttempts: 3,
      backoffRate: 2
    });

    embeddingsTask.addRetry({
      errors: ['States.TaskFailed'],
      interval: cdk.Duration.seconds(5),
      maxAttempts: 3,
      backoffRate: 2
    });

    // Add catch for each task
    textractTask.addCatch(notifyError, {
      errors: ['States.ALL'],
      resultPath: '$.error'
    });

    chunkTask.addCatch(notifyError, {
      errors: ['States.ALL'],
      resultPath: '$.error'
    });

    embeddingsTask.addCatch(notifyError, {
      errors: ['States.ALL'],
      resultPath: '$.error'
    });

    // Success notification
    const successState = new sfn.Pass(this, 'ProcessingComplete', {
      comment: 'Document successfully processed and indexed'
    });

    // Chain with error handling
    const definition = textractTask
      .next(waitForTextract)
      .next(chunkTask)
      .next(embeddingsTask)
      .next(successState);

    notifyError.next(handleError);

    this.ingestionStateMachine = new sfn.StateMachine(this, 'IngestionStateMachine', {
      definitionBody: sfn.DefinitionBody.fromChainable(definition),
      timeout: cdk.Duration.minutes(30),
      tracingEnabled: true,
      logs: {
        destination: new logs.LogGroup(this, 'StateMachineLogGroup', {
          logGroupName: '/aws/vendedlogs/states/strata-ingestion',
          retention: logs.RetentionDays.ONE_WEEK
        }),
        level: sfn.LogLevel.ALL,
        includeExecutionData: true
      }
    });

    // EventBridge rule for S3 uploads
    const ingestionRule = new events.Rule(this, 'IngestionRule', {
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
        detail: {
          bucket: {
            name: [props.documentBucket.bucketName]
          },
          object: {
            key: [{
              prefix: 'documents/'
            }]
          }
        }
      }
    });

    // Transform event before passing to Step Functions
    ingestionRule.addTarget(new targets.SfnStateMachine(this.ingestionStateMachine, {
      input: events.RuleTargetInput.fromObject({
        bucket: events.EventField.fromPath('$.detail.bucket.name'),
        key: events.EventField.fromPath('$.detail.object.key'),
        size: events.EventField.fromPath('$.detail.object.size'),
        etag: events.EventField.fromPath('$.detail.object.etag'),
        tenantId: events.EventField.fromPath('$.detail.object.key').extractPattern(/(tenant-[^\/]+)/),
        documentId: events.EventField.fromPath('$.detail.object.key').extractPattern(/documents\/(.+)\./),
        timestamp: events.EventField.time
      })
    }));

    // CloudWatch Alarms for monitoring
    const failedExecutionsAlarm = new cloudwatch.Alarm(this, 'FailedExecutionsAlarm', {
      metric: this.ingestionStateMachine.metricFailed(),
      threshold: 5,
      evaluationPeriods: 1,
      alarmDescription: 'Too many failed Step Functions executions'
    });

    const dlqMessagesAlarm = new cloudwatch.Alarm(this, 'DLQMessagesAlarm', {
      metric: this.dlq.metricApproximateNumberOfMessagesVisible(),
      threshold: 10,
      evaluationPeriods: 1,
      alarmDescription: 'Messages in DLQ need attention'
    });

    // Outputs
    new cdk.CfnOutput(this, 'StateMachineArn', {
      value: this.ingestionStateMachine.stateMachineArn,
      exportName: `${this.stackName}-StateMachineArn`
    });

    new cdk.CfnOutput(this, 'DLQUrl', {
      value: this.dlq.queueUrl,
      exportName: `${this.stackName}-DLQUrl`
    });
  }
}