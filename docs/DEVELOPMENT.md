# Australian Strata GPT - Development Guide

## Table of Contents
1. [Project Overview](#project-overview)
2. [Development Setup](#development-setup)
3. [Architecture](#architecture)
4. [Testing](#testing)
5. [Deployment](#deployment)
6. [Troubleshooting](#troubleshooting)
7. [Contributing](#contributing)

## Project Overview

Australian Strata GPT is a document Q&A service specifically designed for strata management in Australia. It processes strata documents (PDFs, DOCX, images), extracts text, generates embeddings, and provides accurate answers with legal-grade citations.

### Key Technologies
- **AWS Services**: S3, Lambda, Textract, Bedrock, OpenSearch, Step Functions, DynamoDB
- **Infrastructure**: AWS CDK (TypeScript)
- **Backend**: Python 3.12 with AWS Lambda Powertools
- **Testing**: pytest, moto, unittest

## Development Setup

### Prerequisites
```bash
# Required tools
- AWS CLI v2
- Node.js 18+ and npm
- Python 3.12+
- Docker (for local testing)
- AWS CDK CLI

# Install AWS CDK
npm install -g aws-cdk
```

### Local Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd strata-project

# Install infrastructure dependencies
cd infrastructure/cdk
npm install

# Install Python dependencies for Lambda development
cd ../../backend/lambdas
pip install -r requirements-dev.txt

# Install test dependencies
cd ../../tests
pip install -r requirements-test.txt
```

### Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your AWS account details
AWS_ACCOUNT_ID=your-account-id
AWS_REGION=ap-southeast-2
STACK_PREFIX=StrataGPT
ENVIRONMENT=dev
```

## Architecture

### Document Ingestion Pipeline

```
S3 Upload → EventBridge → Step Functions → Lambda Functions → OpenSearch
                                    ↓
                            1. Textract (OCR)
                            2. Chunk & Sanitize
                            3. Generate Embeddings
                            4. Index to OpenSearch
```

### Lambda Functions

#### 1. Textract Processor (`textract-processor/`)
- Processes documents using AWS Textract
- Handles both sync (images) and async (PDFs) processing
- Updates document metadata in DynamoDB

#### 2. Chunk Sanitizer (`chunk-sanitizer/`)
- Splits documents into ~1000 word chunks with 200 word overlap
- Redacts Australian PII (TFN, ABN, phone numbers, emails)
- Maintains chunk metadata for retrieval

#### 3. Embeddings Generator (`embeddings-generator/`)
- Generates 768-dimensional embeddings using Amazon Titan
- Indexes vectors in OpenSearch with k-NN
- Supports batch processing for efficiency

### Error Handling

All Lambda functions implement:
- AWS Lambda Powertools for structured logging
- Custom metrics emission to CloudWatch
- Exponential backoff retry logic
- Dead Letter Queue (DLQ) for failed messages
- Comprehensive error types for different failure scenarios

## Testing

### Unit Tests
```bash
# Run all unit tests
cd tests
pytest unit/ -v

# Run with coverage
pytest unit/ --cov=backend --cov-report=html

# Run specific test file
pytest unit/lambdas/test_textract_processor.py -v
```

### Integration Tests
```bash
# Run integration tests (requires AWS credentials)
pytest integration/ -v

# Run with specific markers
pytest -m "not slow" -v  # Skip slow tests
pytest -m "integration" -v  # Only integration tests
```

### Test Structure
```
tests/
├── unit/
│   └── lambdas/
│       ├── test_textract_processor.py
│       ├── test_chunk_sanitizer.py
│       └── test_embeddings_generator.py
├── integration/
│   └── test_ingestion_pipeline.py
└── fixtures/
    └── sample_documents/
```

## Deployment

### CDK Deployment

```bash
cd infrastructure/cdk

# First time setup - bootstrap CDK
npm run bootstrap

# Deploy all stacks
npm run deploy

# Deploy specific stack
npx cdk deploy StrataGPT-Network-dev

# View changes before deployment
npm run diff
```

### Stack Dependencies
1. Network Stack (VPC, Subnets)
2. Storage Stack (S3, DynamoDB)
3. OpenSearch Stack (requires Network)
4. Ingestion Stack (requires Storage, OpenSearch)
5. Monitoring Stack (CloudWatch dashboards)

### Deployment Order
```bash
# Deploy in this order to respect dependencies
npx cdk deploy StrataGPT-Network-dev
npx cdk deploy StrataGPT-Storage-dev
npx cdk deploy StrataGPT-OpenSearch-dev
npx cdk deploy StrataGPT-Ingestion-dev
npx cdk deploy StrataGPT-Monitoring-dev
```

## Monitoring & Observability

### CloudWatch Dashboards
- **Ingestion Pipeline**: Document processing metrics
- **Error Tracking**: Failed executions, DLQ messages
- **Performance**: Processing duration, embedding latency

### Key Metrics
- `DocumentsProcessed`: Count of processed documents
- `ProcessingDuration`: Time to process documents
- `EmbeddingLatency`: Time to generate embeddings
- `ChunksGenerated`: Number of chunks created
- `Errors`: Count of processing errors

### Alarms
- Failed Step Functions executions > 5
- DLQ messages > 10
- Processing duration > 5 minutes
- Error rate > 5 per minute

## Troubleshooting

### Common Issues

#### 1. Textract Timeout
```python
# Check CloudWatch Logs
/aws/lambda/textract-processor

# Common causes:
- Large PDF files (>100 pages)
- Poor quality scans
- Complex layouts
```

#### 2. OpenSearch Connection Issues
```python
# Verify endpoint in Lambda environment
OPENSEARCH_ENDPOINT environment variable

# Check security group rules
- Port 443 open from Lambda security group
- VPC endpoints configured correctly
```

#### 3. Bedrock Rate Limits
```python
# Symptoms: Throttling errors in embeddings Lambda

# Solutions:
- Implement exponential backoff
- Set reserved concurrency on Lambda
- Request quota increase
```

### Debug Commands

```bash
# View Step Functions execution
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:...

# Check DLQ messages
aws sqs receive-message \
  --queue-url https://sqs.ap-southeast-2.amazonaws.com/.../strata-ingestion-dlq

# Lambda logs
aws logs tail /aws/lambda/textract-processor --follow
```

## Contributing

### Code Standards

#### Python
- Follow PEP 8
- Use type hints
- Add docstrings to all functions
- Handle exceptions explicitly

#### TypeScript (CDK)
- Use strict mode
- Define interfaces for props
- Add JSDoc comments
- Follow AWS CDK best practices

### Pull Request Process
1. Create feature branch from `main`
2. Add/update tests for new functionality
3. Ensure all tests pass
4. Update documentation
5. Submit PR with clear description

### Commit Message Format
```
feat: Add new feature
fix: Fix bug in component
docs: Update documentation
test: Add unit tests
chore: Update dependencies
```

## Security Considerations

1. **PII Handling**
   - All PII is redacted before storage
   - Audit logs for compliance
   - Encryption at rest and in transit

2. **Access Control**
   - IAM roles follow least privilege
   - Tenant isolation enforced
   - API authentication required

3. **Data Retention**
   - 7-year retention for compliance
   - Automated lifecycle policies
   - Secure deletion procedures

## Performance Optimization

1. **Lambda Optimization**
   - Appropriate memory allocation
   - Connection pooling for OpenSearch
   - Batch processing where possible

2. **Cost Optimization**
   - Reserved concurrency for predictable workloads
   - S3 lifecycle policies
   - On-demand DynamoDB billing

3. **Scalability**
   - Horizontal scaling via Lambda
   - OpenSearch cluster auto-scaling
   - Step Functions for orchestration

## Future Enhancements

1. **Phase 2**: RAG Implementation
   - Kendra integration
   - Advanced prompt engineering
   - Multi-turn conversations

2. **Phase 3**: Multi-tenancy
   - Tenant management dashboard
   - Usage analytics
   - Billing integration

3. **Phase 4**: Production Features
   - Real-time chat
   - Mobile applications
   - Advanced analytics

## Support

For issues or questions:
1. Check CloudWatch Logs
2. Review this documentation
3. Check AWS service health
4. Contact the development team

## License

[Specify your license here]