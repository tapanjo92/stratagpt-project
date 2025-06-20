import * as cdk from 'aws-cdk-lib';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export class PipelineStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const artifactBucket = new s3.Bucket(this, 'ArtifactBucket', {
      bucketName: `strata-pipeline-artifacts-${this.account}-${this.region}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true
    });

    const sourceOutput = new codepipeline.Artifact('SourceOutput');
    const buildOutput = new codepipeline.Artifact('BuildOutput');

    const buildProject = new codebuild.PipelineProject(this, 'BuildProject', {
      projectName: 'strata-build',
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        computeType: codebuild.ComputeType.MEDIUM,
        privileged: true
      },
      environmentVariables: {
        'AWS_ACCOUNT_ID': { value: this.account },
        'AWS_REGION': { value: this.region }
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          pre_build: {
            commands: [
              'echo Logging in to Amazon ECR...',
              'aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com',
              'npm ci',
              'npm run lint',
              'npm run test'
            ]
          },
          build: {
            commands: [
              'echo Build started on `date`',
              'npm run build',
              'cd infrastructure/cdk',
              'npm ci',
              'npm run build',
              'npx cdk synth'
            ]
          },
          post_build: {
            commands: [
              'echo Build completed on `date`'
            ]
          }
        },
        artifacts: {
          files: [
            '**/*'
          ]
        },
        cache: {
          paths: [
            'node_modules/**/*',
            'infrastructure/cdk/node_modules/**/*'
          ]
        }
      })
    });

    buildProject.role?.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEC2ContainerRegistryPowerUser')
    );

    const pipeline = new codepipeline.Pipeline(this, 'Pipeline', {
      pipelineName: 'strata-pipeline',
      artifactBucket,
      stages: [
        {
          stageName: 'Source',
          actions: [
            new codepipeline_actions.S3SourceAction({
              actionName: 'S3Source',
              bucket: artifactBucket,
              bucketKey: 'source.zip',
              output: sourceOutput,
              trigger: codepipeline_actions.S3Trigger.POLL
            })
          ]
        },
        {
          stageName: 'Build',
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: 'Build',
              project: buildProject,
              input: sourceOutput,
              outputs: [buildOutput]
            })
          ]
        },
        {
          stageName: 'Deploy-Dev',
          actions: [
            new codepipeline_actions.CloudFormationCreateUpdateStackAction({
              actionName: 'Deploy-Network',
              templatePath: buildOutput.atPath('infrastructure/cdk/cdk.out/StrataGPT-Network-dev.template.json'),
              stackName: 'StrataGPT-Network-dev',
              adminPermissions: true,
              runOrder: 1
            }),
            new codepipeline_actions.CloudFormationCreateUpdateStackAction({
              actionName: 'Deploy-Storage',
              templatePath: buildOutput.atPath('infrastructure/cdk/cdk.out/StrataGPT-Storage-dev.template.json'),
              stackName: 'StrataGPT-Storage-dev',
              adminPermissions: true,
              runOrder: 2
            }),
            new codepipeline_actions.CloudFormationCreateUpdateStackAction({
              actionName: 'Deploy-OpenSearch',
              templatePath: buildOutput.atPath('infrastructure/cdk/cdk.out/StrataGPT-OpenSearch-dev.template.json'),
              stackName: 'StrataGPT-OpenSearch-dev',
              adminPermissions: true,
              runOrder: 3
            }),
            new codepipeline_actions.CloudFormationCreateUpdateStackAction({
              actionName: 'Deploy-Ingestion',
              templatePath: buildOutput.atPath('infrastructure/cdk/cdk.out/StrataGPT-Ingestion-dev.template.json'),
              stackName: 'StrataGPT-Ingestion-dev',
              adminPermissions: true,
              runOrder: 4
            })
          ]
        }
      ]
    });

    new cdk.CfnOutput(this, 'PipelineName', {
      value: pipeline.pipelineName,
      exportName: `${this.stackName}-PipelineName`
    });
  }
}