import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface IntegrationStackProps extends cdk.StackProps {
  documentBucket: s3.Bucket;
  kendraIngestLambda: lambda.Function;
  ingestionStateMachine?: any; // Step Functions state machine
}

export class IntegrationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: IntegrationStackProps) {
    super(scope, id, props);

    // Use EventBridge Rule instead of direct S3 notifications to avoid circular dependency
    const kendraIngestRule = new events.Rule(this, 'KendraIngestRule', {
      description: 'Trigger Kendra ingestion for new documents',
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
        detail: {
          bucket: {
            name: [props.documentBucket.bucketName]
          },
          object: {
            key: [
              { prefix: 'tenant-' },
              { suffix: '.txt' },
              { suffix: '.pdf' },
              { suffix: '.docx' },
              { suffix: '.doc' },
              { suffix: '.html' }
            ]
          }
        }
      }
    });

    // Add Lambda target with transformation
    kendraIngestRule.addTarget(new targets.LambdaFunction(props.kendraIngestLambda, {
      event: events.RuleTargetInput.fromObject({
        Records: [{
          eventSource: 'aws:s3',
          eventName: 'ObjectCreated:Put',
          s3: {
            bucket: {
              name: events.EventField.fromPath('$.detail.bucket.name')
            },
            object: {
              key: events.EventField.fromPath('$.detail.object.key')
            }
          }
        }]
      }),
      retryAttempts: 2
    }));

    // Rule for document deletions
    const kendraDeleteRule = new events.Rule(this, 'KendraDeleteRule', {
      description: 'Trigger Kendra deletion for removed documents',
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Removed'],
        detail: {
          bucket: {
            name: [props.documentBucket.bucketName]
          },
          object: {
            key: [
              { prefix: 'tenant-' }
            ]
          }
        }
      }
    });

    kendraDeleteRule.addTarget(new targets.LambdaFunction(props.kendraIngestLambda, {
      event: events.RuleTargetInput.fromObject({
        Records: [{
          eventSource: 'aws:s3',
          eventName: 'ObjectRemoved:Delete',
          s3: {
            bucket: {
              name: events.EventField.fromPath('$.detail.bucket.name')
            },
            object: {
              key: events.EventField.fromPath('$.detail.object.key')
            }
          }
        }]
      }),
      retryAttempts: 2
    }));

    // Outputs
    new cdk.CfnOutput(this, 'IntegrationStatus', {
      value: 'S3 to Kendra ingestion wired up successfully',
      description: 'Integration stack deployment status'
    });
  }
}