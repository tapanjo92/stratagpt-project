# Deployment Guide

## Prerequisites

- AWS Account with admin permissions
- AWS CLI configured: `aws configure`
- Node.js 18+ and npm
- Python 3.11+
- Git

## 🚀 Step 1: Initial Deployment

### 1.1 Clone Repository
```bash
git clone <repository-url>
cd stratagpt-project
```

### 1.2 Deploy Infrastructure
```bash
cd infrastructure/cdk
npm install
npm run build

# Deploy all stacks (takes ~20 minutes)
AWS_REGION=ap-south-1 cdk deploy --all --require-approval never
```

### 1.3 Save Outputs
After deployment, save these values:
- API Endpoint URL
- User Pool ID  
- User Pool Client ID
- Kendra Index ID

## 🔧 Step 2: Configure Frontend

### 2.1 Create Environment File
```bash
cd ../../frontend
cat > .env.local << EOF
NEXT_PUBLIC_API_ENDPOINT=<your-api-endpoint>
NEXT_PUBLIC_USER_POOL_ID=<your-user-pool-id>
NEXT_PUBLIC_USER_POOL_CLIENT_ID=<your-client-id>
NEXT_PUBLIC_AWS_REGION=ap-south-1
EOF
```

### 2.2 Install and Run
```bash
npm install
npm run build
npm run dev  # For development
```

## 📄 Step 3: Initialize Documents

### 3.1 Re-index Existing Documents
```bash
cd ../scripts
python3 reindex-all-documents.py
```

### 3.2 Upload Sample Documents
```bash
# Upload to S3 with proper structure
aws s3 cp sample.pdf s3://<bucket>/test-tenant/documents/
```

## 👥 Step 4: Multi-Tenant Setup

### 4.1 Create Tenant Folders
```bash
# Structure: /{tenant-id}/documents/
aws s3api put-object --bucket <bucket> --key tenant-a/documents/
aws s3api put-object --bucket <bucket> --key tenant-b/documents/
```

### 4.2 Create Users
```bash
# Via AWS Console or CLI
aws cognito-idp admin-create-user \
  --user-pool-id <pool-id> \
  --username user@example.com \
  --user-attributes \
    Name=email,Value=user@example.com \
    Name="custom:tenant_id",Value=tenant-a \
    Name="custom:role",Value=owner
```

## ✅ Step 5: Verify Deployment

### 5.1 Test Multi-Tenant Isolation
```bash
cd ..
python3 scripts/test_multi_tenancy.py
```

### 5.2 Test API
```bash
curl https://<api-endpoint>/v1/health
# Should return: {"status": "healthy"}
```

### 5.3 Test RAG Query
```bash
cd scripts
python3 strata-utils.py query "What is the quorum for AGM?"
```

## 🚨 Production Checklist

- [ ] Change Kendra to ENTERPRISE_EDITION
- [ ] Update CORS origins in API stack
- [ ] Configure custom domain for API
- [ ] Set up CloudFront for frontend
- [ ] Enable AWS WAF
- [ ] Configure backup policies
- [ ] Set up monitoring alerts
- [ ] Review and tighten IAM policies
- [ ] Enable AWS CloudTrail
- [ ] Configure budget alerts

## 🔄 Update Deployment

```bash
cd infrastructure/cdk
npm run build
AWS_REGION=ap-south-1 cdk diff  # Review changes
AWS_REGION=ap-south-1 cdk deploy <stack-name>
```

## 🗑️ Cleanup

```bash
# Remove all resources (WARNING: Deletes everything)
AWS_REGION=ap-south-1 cdk destroy --all
```

## 🆘 Troubleshooting

### Kendra Not Indexing
- Check EventBridge rules are enabled
- Verify Lambda has correct permissions
- Run `reindex-all-documents.py`

### API Returns 403
- Check Cognito user has correct attributes
- Verify API Gateway authorizer configuration
- Check CORS settings

### High Costs
- Switch to Kendra Developer Edition for testing
- Remove unused OpenSearch cluster
- Set up cost alerts

---
For architecture details, see [ARCHITECTURE.md](./ARCHITECTURE.md)