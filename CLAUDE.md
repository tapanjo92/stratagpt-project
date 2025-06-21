# Australian Strata GPT - Project Context for Claude

## Project Overview
Building a Q&A system for Australian strata management documents using AWS services.

## Current Status (as of June 20, 2025)

### Completed Phases:
- ✅ **Phase 1.1-1.4**: Infrastructure, ingestion pipeline, vector storage, monitoring
- ✅ **Phase 2.1**: RAG implementation with Kendra and Bedrock
- ✅ **Phase 2.2**: Chat API with conversation management
- ✅ **Phase 2.3**: Frontend application with Next.js
- ✅ **Phase 2.4**: Authentication with Cognito

### Deployed Stacks:
1. **Network Stack**: VPC with CIDR 10.100.0.0/24
2. **Storage Stack**: S3 bucket + DynamoDB tables
3. **OpenSearch Stack**: Single node deployment
4. **Ingestion Stack**: Textract → Chunk → Embeddings pipeline
5. **Monitoring Stack**: CloudWatch dashboards
6. **RAG Stack**: Deployed and functional with custom Kendra ingestion
7. **Integration Stack**: EventBridge rules for automatic document ingestion
8. **API Stack**: REST API with conversation management
9. **Auth Stack**: Cognito User Pools with multi-tenant support

### Recent Updates:
- **UPDATED: Changed Bedrock model to Claude 3 Haiku** (faster, cheaper, fewer rate limits)
- **IMPLEMENTED: Custom Kendra ingestion with proper tenant isolation**
- **FIXED: Tenant isolation now working correctly with batch_put_document API**
- **AUTOMATED: Document ingestion via EventBridge rules in Integration Stack**
- **NEW: Chat API with conversation management and streaming support**
- **NEW: DynamoDB tables for conversation and message persistence**
- **NEW: Next.js frontend with responsive chat interface**
- **NEW: Cognito authentication with role-based access control**
- **NEW: Storybook component library for frontend development**
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

# Test API load (after deployment)
python3 test-api-load.py --url https://your-api-url --concurrent 100

# Run frontend locally
cd ~/strata-project/frontend
npm install
npm run dev

# Run Storybook
npm run storybook
```

### Architecture Summary:
- Document upload → S3 → Textract → Chunking → Embeddings → OpenSearch
- RAG Query → Kendra search → Bedrock (Claude 3 Haiku) → Response with citations
- Chat API → Conversation management → Message history → Contextualized responses
- Evaluation harness with 20 test questions
- Multi-tenant support with proper isolation

### Next Steps:
1. ~~Phase 2.2: Implement Chat API with conversation history~~ ✅ COMPLETE
2. ~~Phase 2.3: Build frontend with chat widget~~ ✅ COMPLETE
3. ~~Phase 2.4: Add authentication with Cognito~~ ✅ COMPLETE
4. **Phase 3.1: Multi-tenant data architecture** (NEXT - Ready to implement)
   - Enhanced DynamoDB schema for tenant metadata
   - Document access control layer
   - Audit logging framework
   - Data retention policies
   - Tenant management API
5. Phase 3.2: Billing & subscription management
6. Phase 3.3: Observability & performance tuning
7. Phase 3.4: Admin dashboard

### Technical Details:
- **Using Bedrock Claude 3 Haiku for answer generation** (optimized for speed/cost)
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