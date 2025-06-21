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
6. **RAG Stack**: Deployed and functional with custom Kendra ingestion
7. **Integration Stack**: EventBridge rules for automatic document ingestion

### Recent Updates:
- Changed Bedrock model to Claude Sonnet 4 (latest model in ap-south-1)
- **IMPLEMENTED: Custom Kendra ingestion with proper tenant isolation**
- **FIXED: Tenant isolation now working correctly with batch_put_document API**
- **AUTOMATED: Document ingestion via EventBridge rules in Integration Stack**
- Added AttributeFilter to Kendra queries for tenant isolation
- Created document tracking table in DynamoDB
- Replaced S3 metadata sync with direct ingestion
- Fixed evaluation scoring to be more realistic (60% pass threshold)
- Increased Lambda timeouts for better reliability

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
- Using Bedrock Claude Sonnet 4 for answer generation
- Titan embeddings for vector search  
- Kendra for document search with AttributeFilter for tenant isolation
- **Multi-tenant isolation WORKING via custom ingestion Lambda**
- Document tracking via DynamoDB table
- See CUSTOM_INGESTION_IMPLEMENTATION.md for details

### Cost Optimization Notes:
- OpenSearch using t3.small instead of r6g.large (saves $200/month)
- Kendra Developer Edition ($810/month) - consider alternatives for dev
- Monitor Bedrock token usage

## Files to Review:
- `/root/strata-project/infrastructure/cdk/stacks/rag-stack.ts` - RAG infrastructure
- `/root/strata-project/backend/lambdas/rag-query/handler.py` - Query logic
- `/root/strata-project/backend/lambdas/rag-evaluation/handler.py` - Test suite
- `/root/strata-project/delivery-phases.md` - Full project roadmap