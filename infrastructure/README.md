# Australian Strata GPT Infrastructure

## Overview
This directory contains the AWS CDK infrastructure code for the Australian Strata GPT project.

## Prerequisites
- AWS CLI configured with appropriate credentials
- Node.js 18+ and npm
- AWS CDK CLI (`npm install -g aws-cdk`)
- Python 3.12+ (for Lambda functions)

## Quick Start

### 1. Install Dependencies
```bash
cd infrastructure/cdk
npm install
```

### 2. Configure Environment
Copy `.env.example` to `.env` and update with your AWS account details:
```bash
cp ../../.env.example .env
```

### 3. Bootstrap CDK (first time only)
```bash
npm run bootstrap
```

### 4. Deploy Infrastructure
```bash
# Deploy all stacks
npm run deploy

# Or deploy specific stacks
npx cdk deploy StrataGPT-Network-dev
npx cdk deploy StrataGPT-Storage-dev
npx cdk deploy StrataGPT-OpenSearch-dev
npx cdk deploy StrataGPT-Ingestion-dev
```

## Stack Architecture

### Network Stack
- VPC with public, private, and isolated subnets
- NAT Gateway for private subnet internet access
- VPC Flow Logs for security monitoring

### Storage Stack
- S3 bucket for document storage with encryption
- DynamoDB tables for tenant and document metadata
- Lifecycle policies for compliance (7-year retention)

### OpenSearch Stack
- OpenSearch domain for vector storage
- Configured for k-NN similarity search
- Fine-grained access control

### Ingestion Stack
- Lambda functions for document processing:
  - Textract processor for OCR
  - Chunk sanitizer for PII redaction
  - Embeddings generator using Bedrock
- Step Functions for orchestration
- EventBridge for S3 event triggers

## Lambda Functions

### Textract Processor
- Processes PDF, DOCX, TIFF, PNG, JPEG files
- Uses async processing for PDFs, sync for images
- Updates document metadata in DynamoDB

### Chunk Sanitizer
- Splits documents into ~1000 word chunks with 200 word overlap
- Redacts Australian PII (emails, phones, TFN, ABN, etc.)
- Maintains chunk metadata for retrieval

### Embeddings Generator
- Generates 768-dimensional embeddings using Titan
- Indexes vectors in OpenSearch
- Supports batch processing for efficiency

## Deployment Commands

```bash
# View changes before deployment
npm run diff

# Deploy with specific parameters
npx cdk deploy --context environment=prod

# Destroy stacks (careful!)
npx cdk destroy --all
```

## Monitoring

After deployment, monitor the stacks via:
- CloudFormation console
- CloudWatch Logs for Lambda functions
- OpenSearch dashboards
- S3 bucket metrics

## Cost Optimization

- OpenSearch uses r6g.large instances (Graviton2)
- Lambda functions configured with appropriate memory
- S3 lifecycle rules move old documents to Glacier
- DynamoDB uses on-demand billing

## Security Considerations

- All data encrypted at rest and in transit
- VPC isolation for OpenSearch
- IAM roles follow least privilege
- PII automatically redacted from documents

## Troubleshooting

### CDK Bootstrap Issues
```bash
# Re-run bootstrap with verbose output
npx cdk bootstrap --verbose
```

### Stack Deployment Failures
1. Check CloudFormation console for detailed errors
2. Review CloudWatch Logs for Lambda errors
3. Ensure service quotas aren't exceeded

### OpenSearch Connection Issues
- Verify security group allows port 443 from VPC
- Check VPC endpoint configuration
- Ensure IAM roles have correct permissions

## Next Steps

After Phase 1 deployment:
1. Test document upload and processing
2. Verify OpenSearch indexing
3. Monitor CloudWatch metrics
4. Proceed to Phase 2 (RAG implementation)