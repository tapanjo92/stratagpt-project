import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as iam from 'aws-cdk-lib/aws-iam';

interface AuthStackProps extends cdk.StackProps {
  // No dependencies needed
}

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    // Create Cognito User Pool
    this.userPool = new cognito.UserPool(this, 'StrataUserPool', {
      userPoolName: `${cdk.Stack.of(this).stackName}-UserPool`,
      selfSignUpEnabled: true,
      signInAliases: {
        email: true,
        username: false,
      },
      autoVerify: {
        email: true,
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
      },
      customAttributes: {
        tenant_id: new cognito.StringAttribute({
          mutable: false,
          minLen: 3,
          maxLen: 64,
        }),
        role: new cognito.StringAttribute({
          mutable: true,
          minLen: 3,
          maxLen: 20,
        }),
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev environment
    });

    // Create app client
    this.userPoolClient = new cognito.UserPoolClient(this, 'UserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: `${cdk.Stack.of(this).stackName}-WebClient`,
      authFlows: {
        userSrp: true,
        userPassword: true, // For development/testing
      },
      generateSecret: false,
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: [
          'http://localhost:3000/auth/callback',
          'https://strata-gpt.example.com/auth/callback', // Update with your domain
        ],
        logoutUrls: [
          'http://localhost:3000',
          'https://strata-gpt.example.com', // Update with your domain
        ],
      },
      readAttributes: new cognito.ClientAttributes()
        .withStandardAttributes({ email: true })
        .withCustomAttributes('tenant_id', 'role'),
      writeAttributes: new cognito.ClientAttributes()
        .withStandardAttributes({ email: true })
        .withCustomAttributes('tenant_id', 'role'),
    });

    // Create admin group
    new cognito.CfnUserPoolGroup(this, 'AdminGroup', {
      userPoolId: this.userPool.userPoolId,
      groupName: 'Admins',
      description: 'Admin users with full access',
      precedence: 1,
    });

    // Create manager group
    new cognito.CfnUserPoolGroup(this, 'ManagerGroup', {
      userPoolId: this.userPool.userPoolId,
      groupName: 'Managers',
      description: 'Strata managers with management access',
      precedence: 2,
    });

    // Create owner group
    new cognito.CfnUserPoolGroup(this, 'OwnerGroup', {
      userPoolId: this.userPool.userPoolId,
      groupName: 'Owners',
      description: 'Lot owners with basic access',
      precedence: 3,
    });

    // Lambda trigger for pre-signup validation
    const preSignupLambda = new cdk.aws_lambda.Function(this, 'PreSignupFunction', {
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: cdk.aws_lambda.Code.fromInline(`
import json

def handler(event, context):
    # Validate tenant_id
    tenant_id = event['request']['userAttributes'].get('custom:tenant_id', '')
    if not tenant_id or len(tenant_id) < 3:
        raise Exception('Invalid tenant_id')
    
    # Auto-confirm for development (remove in production)
    event['response']['autoConfirmUser'] = True
    event['response']['autoVerifyEmail'] = True
    
    return event
      `),
    });

    this.userPool.addTrigger(cognito.UserPoolOperation.PRE_SIGN_UP, preSignupLambda);

    // Note: Post-confirmation Lambda removed to avoid circular dependency
    // Users will need to be manually added to groups or we'll implement this differently
    // This can be done through the API or admin interface

    // Outputs
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
    });

    new cdk.CfnOutput(this, 'CognitoDomain', {
      value: `https://cognito-idp.${this.region}.amazonaws.com`,
      description: 'Cognito domain',
    });
  }
}