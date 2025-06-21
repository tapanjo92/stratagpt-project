# System Architecture

## Overview

Australian Strata GPT is a serverless, multi-tenant SaaS platform built on AWS. The system uses event-driven architecture with complete tenant isolation.

## Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Next.js App   │────▶│  API Gateway    │────▶│    Lambda       │
│   (Frontend)    │     │  + Authorizer   │     │   Functions     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                        ┌─────────────────────────────────┼─────────────────┐
                        │                                 │                 │
                        ▼                                 ▼                 ▼
                ┌─────────────────┐         ┌─────────────────┐   ┌─────────────┐
                │                 │         │                 │   │             │
                │     Kendra      │         │    DynamoDB     │   │   Bedrock   │
                │  (Doc Search)   │         │  (Metadata)     │   │  (Claude)   │
                │                 │         │                 │   │             │
                └─────────────────┘         └─────────────────┘   └─────────────┘
                        ▲                                                   
                        │                                                   
                ┌───────┴─────────┐                                        
                │                 │                                        
                │       S3        │                                        
                │  (Documents)    │                                        
                │                 │                                        
                └─────────────────┘                                        
```

## Components

### Frontend Layer
- **Technology**: Next.js 14, TypeScript, Tailwind CSS
- **Authentication**: AWS Amplify with Cognito
- **Features**: Real-time chat, document upload, markdown rendering

### API Layer
- **API Gateway**: REST API with request validation
- **Authorization**: Cognito User Pool authorizer
- **Rate Limiting**: Usage plans (Basic/Standard/Premium)
- **CORS**: Domain whitelisting

### Compute Layer
- **Lambda Functions**:
  - `ChatResolver`: Handles chat messages, maintains context
  - `ConversationManager`: CRUD for conversations
  - `RAGQuery`: Searches Kendra and generates responses
  - `KendraIngest`: Custom document ingestion with metadata

### Storage Layer

#### S3 Buckets
```
strata-documents-{account}-{region}/
├── tenant-a/
│   └── documents/
│       ├── bylaws.pdf
│       └── agm-minutes.docx
└── tenant-b/
    └── documents/
        └── capital-works.pdf
```

#### DynamoDB Tables
1. **Conversations**
   - PK: tenant_id
   - SK: conversation_id
   - Attributes: title, created_at, user_id

2. **Messages**
   - PK: conversation_id  
   - SK: timestamp_message_id
   - GSI: tenant_id (for tenant queries)

3. **Document Tracking**
   - PK: document_id
   - GSI: tenant_id, ingested_at

### Search & AI Layer

#### Kendra
- **Index**: Single index with AttributeFilter
- **Metadata**: tenant_id, document_type, upload_date
- **Ingestion**: Custom Lambda (not S3 data source)

#### Bedrock
- **Model**: Claude 3 Haiku (optimized for speed/cost)
- **Context**: 10 messages maintained
- **Response Time**: ~2-3 seconds

## Data Flow

### Document Ingestion
1. User uploads to S3 via presigned URL
2. EventBridge detects S3 event
3. Triggers KendraIngest Lambda
4. Lambda adds tenant_id attribute
5. Document indexed in Kendra

### Query Processing
1. User sends query via API
2. API Gateway validates request
3. ChatResolver Lambda:
   - Fetches conversation history
   - Calls RAGQuery Lambda
4. RAGQuery Lambda:
   - Searches Kendra with tenant filter
   - Generates response with Bedrock
   - Returns with citations
5. Response saved to DynamoDB

## Security

### Multi-Tenant Isolation
- **Kendra**: AttributeFilter on tenant_id
- **DynamoDB**: Partition key includes tenant_id
- **S3**: Folder structure by tenant
- **API**: X-Tenant-Id header validation

### Encryption
- **At Rest**: S3 (KMS), DynamoDB (AWS Managed)
- **In Transit**: HTTPS everywhere
- **Secrets**: None stored in code

### IAM Policies
- Least privilege principle
- Specific resource ARNs (no wildcards)
- Service-to-service permissions only

## Scalability

### Current Limits
- Kendra: 100 queries/second
- API Gateway: 100 TPS (configurable)
- Lambda: 1000 concurrent executions
- DynamoDB: On-demand scaling

### Cost Optimization
- Lambda: Memory optimized (1769MB for compute)
- Bedrock: Claude 3 Haiku (cheapest model)
- DynamoDB: Pay-per-request billing
- S3: Lifecycle policies for archival

## Monitoring

### CloudWatch
- Lambda logs with 1 week retention
- API Gateway access logs
- Custom metrics for query latency

### Alarms
- Lambda errors > 1%
- API 4xx/5xx > 5%
- Kendra throttling
- DynamoDB throttling

## Deployment

### Infrastructure as Code
- AWS CDK v2 (TypeScript)
- 10 CloudFormation stacks
- Environment: dev/staging/prod

### CI/CD Pipeline (Future)
- GitHub Actions
- Automated testing
- Blue/green deployments
- Rollback capabilities

---
For deployment instructions, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)