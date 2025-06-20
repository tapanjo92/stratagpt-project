#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../stacks/network-stack';
import { StorageStack } from '../stacks/storage-stack';
import { ComputeStack } from '../stacks/compute-stack';
import { IngestionStack } from '../stacks/ingestion-stack';
import { OpenSearchStack } from '../stacks/opensearch-stack';
import { MonitoringStack } from '../stacks/monitoring-stack';

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID,
  region: process.env.CDK_DEFAULT_REGION || 'ap-southeast-2'
};

const stackPrefix = app.node.tryGetContext('stackPrefix') || 'StrataGPT';
const environment = app.node.tryGetContext('environment') || 'dev';

const networkStack = new NetworkStack(app, `${stackPrefix}-Network-${environment}`, {
  env,
  description: 'Network infrastructure for Strata GPT'
});

const storageStack = new StorageStack(app, `${stackPrefix}-Storage-${environment}`, {
  env,
  description: 'Storage resources for Strata GPT'
});

const openSearchStack = new OpenSearchStack(app, `${stackPrefix}-OpenSearch-${environment}`, {
  env,
  vpc: networkStack.vpc,
  description: 'OpenSearch cluster for vector storage'
});

const computeStack = new ComputeStack(app, `${stackPrefix}-Compute-${environment}`, {
  env,
  vpc: networkStack.vpc,
  description: 'Compute resources for Strata GPT'
});

const ingestionStack = new IngestionStack(app, `${stackPrefix}-Ingestion-${environment}`, {
  env,
  documentBucket: storageStack.documentBucket,
  openSearchDomain: openSearchStack.domain,
  description: 'Document ingestion pipeline'
});

const monitoringStack = new MonitoringStack(app, `${stackPrefix}-Monitoring-${environment}`, {
  env,
  description: 'Monitoring and observability resources'
});

app.synth();