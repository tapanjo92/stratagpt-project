import * as cdk from 'aws-cdk-lib';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface OpenSearchStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
}

export class OpenSearchStack extends cdk.Stack {
  public readonly domain: opensearch.Domain;

  constructor(scope: Construct, id: string, props: OpenSearchStackProps) {
    super(scope, id, props);

    const domainName = 'strata-vectors';

    const securityGroup = new ec2.SecurityGroup(this, 'OpenSearchSecurityGroup', {
      vpc: props.vpc,
      description: 'Security group for OpenSearch domain',
      allowAllOutbound: true
    });

    securityGroup.addIngressRule(
      ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.tcp(443),
      'Allow HTTPS from VPC'
    );

    this.domain = new opensearch.Domain(this, 'VectorSearchDomain', {
      domainName,
      version: opensearch.EngineVersion.OPENSEARCH_2_11,
      capacity: {
        masterNodes: 0,
        dataNodes: 2,
        dataNodeInstanceType: 'r6g.large.search'
      },
      ebs: {
        volumeSize: 100,
        volumeType: ec2.EbsDeviceVolumeType.GP3
      },
      nodeToNodeEncryption: true,
      encryptionAtRest: {
        enabled: true
      },
      vpc: props.vpc,
      vpcSubnets: [{
        subnetType: ec2.SubnetType.PRIVATE_ISOLATED
      }],
      securityGroups: [securityGroup],
      enforceHttps: true,
      fineGrainedAccessControl: {
        masterUserArn: new iam.ArnPrincipal(
          `arn:aws:iam::${this.account}:root`
        ).arn
      },
      logging: {
        slowSearchLogEnabled: true,
        appLogEnabled: true,
        slowIndexLogEnabled: true
      },
      removalPolicy: cdk.RemovalPolicy.RETAIN
    });

    const accessPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.AnyPrincipal()],
      actions: ['es:*'],
      resources: [`${this.domain.domainArn}/*`],
      conditions: {
        IpAddress: {
          'aws:SourceIp': [props.vpc.vpcCidrBlock]
        }
      }
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
  }
}