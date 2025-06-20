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
6. **RAG Stack**: Deployed and functional

### Recent Updates:
- Changed Bedrock model from Claude 3 Opus to Claude 3 Haiku (regional availability)
- Implemented retry logic for Kendra throttling
- Added tenant_id bypass option ('ALL') for testing
- Increased Lambda timeouts for better reliability
- Added evaluation harness with 20 test questions

### Key Configuration:
- **Region**: ap-south-1 (Mumbai)
- **Account**: 809555764832
- **Stack Prefix**: StrataGPT
- **Environment**: dev

### Important Commands:
```bash
# Deploy all stacks
cd ~/strata-project/infrastructure/cdk
npm run build
AWS_REGION=ap-south-1 cdk deploy --all

# Test RAG query
cd ~/strata-project/scripts
python3 strata-utils.py query "What is the quorum for an AGM?"

# Run evaluation
python3 run-evaluation.py

# Check Kendra status
python3 strata-utils.py status
```

### Architecture Summary:
- Document upload → S3 → Textract → Chunking → Embeddings → OpenSearch
- RAG Query → Kendra search → Bedrock (Claude 3 Haiku) → Response with citations
- Evaluation harness with 20 test questions
- Multi-tenant support (currently using bypass for testing)

### Next Steps:
1. Phase 2.2: Implement Chat API with conversation history
2. Phase 2.3: Add admin portal for document management
3. Phase 2.4: Implement feedback and improvement system
4. Phase 3: Scale to production with multi-region support

### Technical Details:
- Using Bedrock Claude 3 Haiku for answer generation (Opus not available in ap-south-1)
- Titan embeddings for vector search
- Kendra Developer Edition for document search
- Multi-tenant isolation via tenant_id (currently bypassed with 'ALL' for testing)

### Cost Optimization Notes:
- OpenSearch using t3.small instead of r6g.large (saves $200/month)
- Kendra Developer Edition ($810/month) - consider alternatives for dev
- Monitor Bedrock token usage

## Files to Review:
- `/root/strata-project/infrastructure/cdk/stacks/rag-stack.ts` - RAG infrastructure
- `/root/strata-project/backend/lambdas/rag-query/handler.py` - Query logic
- `/root/strata-project/backend/lambdas/rag-evaluation/handler.py` - Test suite
- `/root/strata-project/delivery-phases.md` - Full project roadmap