import * as cdk from 'aws-cdk-lib';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export interface OpenSearchStackProps extends cdk.StackProps {
  // Remove VPC requirement for simpler setup
}

export class OpenSearchStack extends cdk.Stack {
  public readonly domain: opensearch.Domain;

  constructor(scope: Construct, id: string, props?: OpenSearchStackProps) {
    super(scope, id, props);

    const domainName = 'strata-vectors';

    // Simpler configuration without VPC
    this.domain = new opensearch.Domain(this, 'VectorSearchDomain', {
      domainName,
      version: opensearch.EngineVersion.OPENSEARCH_2_11,
      capacity: {
        masterNodes: 0,
        dataNodes: 1,  // Start with single node for cost optimization
        dataNodeInstanceType: 't3.small.search'  // Smaller instance for testing
      },
      ebs: {
        volumeSize: 20,  // Smaller volume for testing
        volumeType: ec2.EbsDeviceVolumeType.GP3
      },
      nodeToNodeEncryption: true,
      encryptionAtRest: {
        enabled: true
      },
      enforceHttps: true,
      useUnsignedBasicAuth: true,  // Simple auth for testing
      fineGrainedAccessControl: {
        masterUserName: 'admin',
        masterUserPassword: cdk.SecretValue.unsafePlainText('StrataAdmin123!')  // Change in production
      },
      logging: {
        slowSearchLogEnabled: false,  // Disable to reduce costs
        appLogEnabled: false,
        slowIndexLogEnabled: false
      },
      removalPolicy: cdk.RemovalPolicy.DESTROY  // For easy cleanup
    });

    // Simple access policy
    const accessPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ArnPrincipal(`arn:aws:iam::${this.account}:root`)],
      actions: ['es:*'],
      resources: [`${this.domain.domainArn}/*`]
    });

    this.domain.addAccessPolicies(accessPolicy);

    new cdk.CfnOutput(this, 'OpenSearchDomainEndpoint', {
      value: this.domain.domainEndpoint,
      exportName: `${this.stackName}-OpenSearchEndpoint`
    });

    new cdk.CfnOutput(this, 'OpenSearchDomainArn', {
      value: this.domain.domainArn,
      exportName: `${this.stackName}-OpenSearchArn`
    });

    new cdk.CfnOutput(this, 'OpenSearchUsername', {
      value: 'admin',
      description: 'OpenSearch master username'
    });
  }
}