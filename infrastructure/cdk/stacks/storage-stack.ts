import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as kms from 'aws-cdk-lib/aws-kms';
import { Construct } from 'constructs';

export class StorageStack extends cdk.Stack {
  public readonly documentBucket: s3.Bucket;
  public readonly tenantTable: dynamodb.Table;
  public readonly documentMetadataTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const encryptionKey = new kms.Key(this, 'StrataEncryptionKey', {
      description: 'KMS key for Strata GPT encryption',
      enableKeyRotation: true,
      alias: 'strata-gpt-key'
    });

    this.documentBucket = new s3.Bucket(this, 'DocumentBucket', {
      bucketName: `strata-documents-${this.account}-${this.region}`,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      lifecycleRules: [
        {
          id: 'MoveToGlacierAfter7Years',
          enabled: true,
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(2555)
            }
          ]
        },
        {
          id: 'DeleteNonCurrentVersions',
          enabled: true,
          noncurrentVersionExpiration: cdk.Duration.days(30)
        }
      ],
      cors: [
        {
          allowedHeaders: ['*'],
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
          allowedOrigins: ['*'],
          exposedHeaders: ['ETag'],
          maxAge: 3000
        }
      ],
      serverAccessLogsPrefix: 'access-logs/',
      eventBridgeEnabled: true
    });

    this.tenantTable = new dynamodb.Table(this, 'TenantTable', {
      tableName: 'strata-tenants',
      partitionKey: { name: 'tenantId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
    });

    this.tenantTable.addGlobalSecondaryIndex({
      indexName: 'TenantByDate',
      partitionKey: { name: 'createdDate', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'tenantId', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL
    });

    this.documentMetadataTable = new dynamodb.Table(this, 'DocumentMetadataTable', {
      tableName: 'strata-document-metadata',
      partitionKey: { name: 'tenantId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'documentId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
    });

    this.documentMetadataTable.addGlobalSecondaryIndex({
      indexName: 'DocumentByUploadDate',
      partitionKey: { name: 'tenantId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'uploadDate', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL
    });

    new cdk.CfnOutput(this, 'DocumentBucketName', {
      value: this.documentBucket.bucketName,
      exportName: `${this.stackName}-DocumentBucketName`
    });

    new cdk.CfnOutput(this, 'TenantTableName', {
      value: this.tenantTable.tableName,
      exportName: `${this.stackName}-TenantTableName`
    });
  }
}