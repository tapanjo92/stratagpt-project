# Australian Strata GPT - Project Context for Claude

## Project Overview
Building a Q&A system for Australian strata management documents using AWS services.

## Current Status (as of June 20, 2025)

### Completed Phases:
- ✅ **Phase 1.1-1.4**: Infrastructure, ingestion pipeline, vector storage, monitoring
- ✅ **Phase 2.1**: RAG implementation with Kendra and Bedrock

### Deployed Stacks:
1. **Network Stack**: VPC with CIDR 10.100.0.0/24
2. **Storage Stack**: S3 bucket + DynamoDB tables
3. **OpenSearch Stack**: Single node deployment
4. **Ingestion Stack**: Textract → Chunk → Embeddings pipeline
5. **Monitoring Stack**: CloudWatch dashboards
6. **RAG Stack**: In progress (fixing Kendra cron schedule)

### Current Issue:
- RAG stack deployment failed due to Kendra schedule format
- Fixed: Changed from `rate(1 hour)` to `cron(0 * * * ? *)`
- Need to: Delete failed stack and redeploy

### Key Configuration:
- **Region**: ap-south-1 (Mumbai)
- **Account**: 809555764832
- **Stack Prefix**: StrataGPT
- **Environment**: dev

### Important Commands:
```bash
# Deploy RAG stack
cd ~/strata-project/infrastructure/cdk
AWS_REGION=ap-south-1 cdk deploy StrataGPT-RAG-dev

# Test RAG query
AWS_REGION=ap-south-1 aws lambda invoke \
  --function-name StrataGPT-RAG-dev-RAGQueryFunction \
  --payload '{"question": "What is the quorum for an AGM?", "tenant_id": "test-tenant"}' \
  response.json
```

### Architecture Summary:
- Document upload → S3 → Textract → Chunking → Embeddings → OpenSearch
- RAG Query → Kendra search → Bedrock (Claude 3 Opus) → Response with citations
- Evaluation harness with 20 test questions

### Next Steps:
1. Complete RAG stack deployment
2. Upload sample documents
3. Run evaluation suite
4. Move to Phase 2.2 (Chat API)

### Technical Details:
- Using Bedrock Claude 3 Opus for answer generation
- Titan embeddings for vector search
- Kendra Developer Edition for document search
- Multi-tenant isolation via tenant_id

### Cost Optimization Notes:
- OpenSearch using t3.small instead of r6g.large (saves $200/month)
- Kendra Developer Edition ($810/month) - consider alternatives for dev
- Monitor Bedrock token usage

## Files to Review:
- `/root/strata-project/infrastructure/cdk/stacks/rag-stack.ts` - RAG infrastructure
- `/root/strata-project/backend/lambdas/rag-query/handler.py` - Query logic
- `/root/strata-project/backend/lambdas/rag-evaluation/handler.py` - Test suite
- `/root/strata-project/delivery-phases.md` - Full project roadmap