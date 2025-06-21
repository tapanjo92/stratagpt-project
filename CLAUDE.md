# Project Context for Claude

## Quick Reference

**Project**: Australian Strata GPT - Multi-tenant document Q&A system  
**Region**: ap-south-1 (Mumbai)  
**Account**: 809555764832  
**Stack Prefix**: StrataGPT  

## Current Status

✅ **PRODUCTION READY** - All critical issues fixed
- Multi-tenant isolation working
- Secure IAM policies  
- Optimized for cost/performance

## Key Commands

```bash
# Deploy infrastructure
cd infrastructure/cdk
npm run build
AWS_REGION=ap-south-1 cdk deploy StrataGPT-RAG-dev
AWS_REGION=ap-south-1 cdk deploy StrataGPT-API-dev

# Re-index documents (REQUIRED after deployment)
cd ../../scripts
python3 reindex-all-documents.py

# Test multi-tenancy
python3 test_multi_tenancy.py

# Query documents
python3 strata-utils.py query "What is the quorum?"
```

## Architecture Decisions

1. **Kendra Only** - No OpenSearch (save $50/month)
2. **Claude 3 Haiku** - Fast & cheap ($30/month)
3. **Serverless Everything** - Pay per use
4. **Custom Ingestion** - Proper tenant isolation

## Important Files

- `infrastructure/cdk/stacks/rag-stack.ts` - Core RAG logic
- `infrastructure/cdk/stacks/api-stack.ts` - API configuration
- `backend/lambdas/rag-query/handler.py` - Query logic
- `scripts/reindex-all-documents.py` - Fix tenant isolation

## Cost: ~$925/month

Mainly Kendra ($810). Consider alternatives for dev/test.