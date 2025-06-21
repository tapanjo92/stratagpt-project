import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';

interface ApiStackProps extends cdk.StackProps {
  kendraIndexId: string;
  ragQueryFunctionArn: string;
  userPool?: cognito.IUserPool;
}

export class ApiStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;
  public readonly conversationsTable: dynamodb.Table;
  public readonly messagesTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    // DynamoDB Tables for conversation management
    this.conversationsTable = new dynamodb.Table(this, 'ConversationsTable', {
      tableName: `${cdk.Stack.of(this).stackName}-Conversations`,
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'conversation_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'ttl',
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true
      },
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
    });

    this.messagesTable = new dynamodb.Table(this, 'MessagesTable', {
      tableName: `${cdk.Stack.of(this).stackName}-Messages`,
      partitionKey: { name: 'conversation_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp_message_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true
      },
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
    });

    // Add GSI for querying messages by tenant
    this.messagesTable.addGlobalSecondaryIndex({
      indexName: 'tenant-timestamp-index',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp_message_id', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Chat Resolver Lambda with streaming
    const chatResolverFunction = new PythonFunction(this, 'ChatResolverFunction', {
      functionName: `${cdk.Stack.of(this).stackName}-ChatResolver`,
      entry: '../../backend/lambdas/chat-resolver',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler',
      timeout: cdk.Duration.seconds(300),
      memorySize: 1769,  // Optimal for CPU-bound tasks (1 vCPU threshold)
      environment: {
        KENDRA_INDEX_ID: props.kendraIndexId,
        CONVERSATIONS_TABLE: this.conversationsTable.tableName,
        MESSAGES_TABLE: this.messagesTable.tableName,
        RAG_FUNCTION_ARN: props.ragQueryFunctionArn,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // Grant permissions
    this.conversationsTable.grantReadWriteData(chatResolverFunction);
    this.messagesTable.grantReadWriteData(chatResolverFunction);

    // Grant permission to invoke RAG query function
    chatResolverFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['lambda:InvokeFunction'],
      resources: [props.ragQueryFunctionArn],
    }));

    // Grant Bedrock permissions with specific model ARN
    chatResolverFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
      ],
      resources: [
        `arn:aws:bedrock:${this.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0`
      ],
    }));

    // Conversation Manager Lambda
    const conversationManagerFunction = new PythonFunction(this, 'ConversationManagerFunction', {
      functionName: `${cdk.Stack.of(this).stackName}-ConversationManager`,
      entry: '../../backend/lambdas/conversation-manager',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler',
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,  // Lightweight DynamoDB operations
      environment: {
        CONVERSATIONS_TABLE: this.conversationsTable.tableName,
        MESSAGES_TABLE: this.messagesTable.tableName,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // Grant permissions
    this.conversationsTable.grantReadWriteData(conversationManagerFunction);
    this.messagesTable.grantReadWriteData(conversationManagerFunction);

    // Create Cognito authorizer if user pool is provided
    let authorizer: apigateway.CognitoUserPoolsAuthorizer | undefined;
    if (props.userPool) {
      authorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'ApiAuthorizer', {
        cognitoUserPools: [props.userPool],
        authorizerName: `${cdk.Stack.of(this).stackName}-Authorizer`,
      });
    }

    // API Gateway
    this.api = new apigateway.RestApi(this, 'ChatApi', {
      restApiName: `${cdk.Stack.of(this).stackName}-ChatAPI`,
      description: 'Australian Strata GPT Chat API',
      deployOptions: {
        stageName: 'v1',
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
        throttlingRateLimit: 100,
        throttlingBurstLimit: 200,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: [
          'https://stratagpt.com.au',
          'https://app.stratagpt.com.au',
          'http://localhost:3000',  // Development only
        ],
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Tenant-Id',
        ],
        allowCredentials: true,
      },
    });

    // Request Validator
    const requestValidator = new apigateway.RequestValidator(this, 'RequestValidator', {
      restApi: this.api,
      requestValidatorName: 'Validate body and parameters',
      validateRequestBody: true,
      validateRequestParameters: true,
    });

    // API Models
    const errorResponseModel = this.api.addModel('ErrorResponseModel', {
      contentType: 'application/json',
      modelName: 'ErrorResponse',
      schema: {
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          error: { type: apigateway.JsonSchemaType.STRING },
          message: { type: apigateway.JsonSchemaType.STRING },
          requestId: { type: apigateway.JsonSchemaType.STRING },
        },
        required: ['error', 'message'],
      },
    });

    const createConversationModel = this.api.addModel('CreateConversationModel', {
      contentType: 'application/json',
      modelName: 'CreateConversation',
      schema: {
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          title: { type: apigateway.JsonSchemaType.STRING },
          metadata: { type: apigateway.JsonSchemaType.OBJECT },
        },
      },
    });

    const sendMessageModel = this.api.addModel('SendMessageModel', {
      contentType: 'application/json',
      modelName: 'SendMessage',
      schema: {
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          message: { type: apigateway.JsonSchemaType.STRING },
          stream: { type: apigateway.JsonSchemaType.BOOLEAN },
        },
        required: ['message'],
      },
    });

    // Health check endpoint
    const health = this.api.root.addResource('health');
    health.addMethod('GET', new apigateway.MockIntegration({
      integrationResponses: [{
        statusCode: '200',
        responseTemplates: {
          'application/json': JSON.stringify({ status: 'healthy' }),
        },
      }],
      requestTemplates: {
        'application/json': '{"statusCode": 200}',
      },
    }), {
      methodResponses: [{ statusCode: '200' }],
    });

    // Chat endpoints
    const chat = this.api.root.addResource('chat');
    const conversations = chat.addResource('conversations');
    
    // POST /chat/conversations - Create new conversation
    conversations.addMethod('POST', 
      new apigateway.LambdaIntegration(conversationManagerFunction, {
        requestTemplates: {
          'application/json': JSON.stringify({
            action: 'create',
            tenantId: "$context.requestOverride.header.X-Tenant-Id",
            userId: "$context.authorizer.claims.sub",
            body: "$input.json('$')",
          }),
        },
      }), {
        requestValidator,
        requestModels: {
          'application/json': createConversationModel,
        },
        ...(authorizer && { authorizer }),
        methodResponses: [
          { statusCode: '200' },
          { 
            statusCode: '400',
            responseModels: {
              'application/json': errorResponseModel,
            },
          },
        ],
      }
    );

    // Conversation-specific endpoints
    const conversation = conversations.addResource('{conversationId}');
    
    // GET /chat/conversations/{conversationId} - Get conversation history
    conversation.addMethod('GET',
      new apigateway.LambdaIntegration(conversationManagerFunction, {
        requestTemplates: {
          'application/json': JSON.stringify({
            action: 'get',
            conversationId: "$input.params('conversationId')",
            tenantId: "$context.requestOverride.header.X-Tenant-Id",
            userId: "$context.authorizer.claims.sub",
          }),
        },
      }), {
        requestParameters: {
          'method.request.path.conversationId': true,
          'method.request.header.X-Tenant-Id': true,
        },
        ...(authorizer && { authorizer }),
        methodResponses: [
          { statusCode: '200' },
          { statusCode: '404' },
        ],
      }
    );

    // Messages endpoint
    const messages = conversation.addResource('messages');
    
    // POST /chat/conversations/{conversationId}/messages - Send message
    messages.addMethod('POST',
      new apigateway.LambdaIntegration(chatResolverFunction, {
        requestTemplates: {
          'application/json': JSON.stringify({
            conversationId: "$input.params('conversationId')",
            tenantId: "$context.requestOverride.header.X-Tenant-Id",
            userId: "$context.authorizer.claims.sub",
            body: "$input.json('$')",
          }),
        },
      }), {
        requestValidator,
        requestModels: {
          'application/json': sendMessageModel,
        },
        requestParameters: {
          'method.request.path.conversationId': true,
          'method.request.header.X-Tenant-Id': true,
        },
        ...(authorizer && { authorizer }),
        methodResponses: [
          { statusCode: '200' },
          { statusCode: '400' },
        ],
      }
    );

    // Create usage plans for different tiers
    const basicUsagePlan = this.api.addUsagePlan('BasicUsagePlan', {
      name: 'Basic',
      description: 'Basic tier - 100 requests per day',
      throttle: {
        rateLimit: 10,
        burstLimit: 20
      },
      quota: {
        limit: 100,
        period: apigateway.Period.DAY
      }
    });

    const standardUsagePlan = this.api.addUsagePlan('StandardUsagePlan', {
      name: 'Standard',
      description: 'Standard tier - 1000 requests per day',
      throttle: {
        rateLimit: 50,
        burstLimit: 100
      },
      quota: {
        limit: 1000,
        period: apigateway.Period.DAY
      }
    });

    const premiumUsagePlan = this.api.addUsagePlan('PremiumUsagePlan', {
      name: 'Premium',
      description: 'Premium tier - 10000 requests per day',
      throttle: {
        rateLimit: 100,
        burstLimit: 200
      },
      quota: {
        limit: 10000,
        period: apigateway.Period.DAY
      }
    });

    // Add stages to usage plans
    basicUsagePlan.addApiStage({ stage: this.api.deploymentStage });
    standardUsagePlan.addApiStage({ stage: this.api.deploymentStage });
    premiumUsagePlan.addApiStage({ stage: this.api.deploymentStage });

    // Output API endpoint
    new cdk.CfnOutput(this, 'ApiEndpoint', {
      value: this.api.url,
      description: 'Chat API endpoint URL',
    });

    new cdk.CfnOutput(this, 'ConversationsTableName', {
      value: this.conversationsTable.tableName,
      description: 'DynamoDB Conversations table name',
    });

    new cdk.CfnOutput(this, 'MessagesTableName', {
      value: this.messagesTable.tableName,
      description: 'DynamoDB Messages table name',
    });
  }
}