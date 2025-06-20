# CDK Deployment Notes - Updated Configuration

## Changes Made for Production Deployment

### 1. Bedrock Model Configuration
- **Changed from**: Claude 3 Opus (`anthropic.claude-3-opus-20240229-v1:0`)
- **Changed to**: Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`)
- **Reason**: Claude 3 Opus is not available in ap-south-1 region

### 2. Lambda Timeout Adjustments
- **RAG Query Lambda**: Increased from 30s to 60s
- **Evaluation Lambda**: Increased from 5m to 10m
- **Reason**: Prevent timeouts during complex queries and evaluation runs

### 3. Concurrency Configuration
- **Evaluation Lambda**: Set `reservedConcurrentExecutions: 1`
- **Reason**: Prevent Kendra throttling from concurrent evaluation runs

### 4. Kendra Data Source Configuration
- **inclusionPrefixes**: Changed to `['test-tenant/documents/']`
- **metadata s3Prefix**: Changed to `'test-tenant/metadata/'`
- **Reason**: Match actual document structure in S3

### 5. Lambda Handler Updates
- Added retry logic for Kendra throttling
- Added tenant_id bypass option (use 'ALL' to skip filtering)
- Enhanced error logging

## Deployment Commands

```bash
# Navigate to CDK directory
cd /root/strata-project/infrastructure/cdk

# Build the TypeScript
npm run build

# Deploy the updated stack
AWS_REGION=ap-south-1 cdk deploy StrataGPT-RAG-dev --require-approval never

# After deployment, re-upload documents if needed
cd /root/strata-project/scripts
./upload-sample-documents.sh
python3 trigger-kendra-sync.py
```

## Testing After Deployment

```bash
# Test RAG query (with tenant bypass)
AWS_REGION=ap-south-1 aws lambda invoke \
  --function-name [GET_FROM_CDK_OUTPUT] \
  --cli-binary-format raw-in-base64-out \
  --payload '{"question": "What is the quorum for an AGM?", "tenant_id": "ALL"}' \
  response.json

# Check response
cat response.json | jq '.'
```

## Known Issues & Workarounds

1. **Tenant Filtering**: Not working due to Kendra metadata association issue
   - **Workaround**: Use `tenant_id="ALL"` in queries

2. **Model Selection**: Claude 3 Opus not available in ap-south-1
   - **Solution**: Using Claude 3 Haiku which provides good performance

3. **Evaluation Scoring**: Low accuracy scores despite good responses
   - **Note**: This is a scoring algorithm issue, not response quality

## Next Steps

After deployment, consider:
1. Implementing OpenSearch-based RAG as alternative to Kendra
2. Creating API Gateway endpoints for Phase 2.2
3. Adding DynamoDB for conversation history