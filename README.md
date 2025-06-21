# Australian Strata GPT

AI-powered document Q&A system for Australian strata management with enterprise-grade multi-tenant isolation.

## 🚀 Quick Start

```bash
# Prerequisites
- AWS Account with appropriate permissions
- Node.js 18+ and Python 3.11+
- AWS CLI configured with credentials

# Clone and setup
git clone <repository>
cd stratagpt-project

# Deploy infrastructure
cd infrastructure/cdk
npm install
npm run build
AWS_REGION=ap-south-1 cdk deploy --all

# Configure frontend
cd ../../frontend
cp .env.example .env.local
# Edit .env.local with your API endpoint and Cognito details
npm install
npm run dev
```

## 📋 Features

- **Multi-tenant SaaS** - Complete data isolation between tenants
- **Document Processing** - Supports PDF, DOCX, TXT with automatic text extraction
- **AI-Powered Q&A** - Uses AWS Bedrock (Claude 3 Haiku) for accurate responses
- **Real-time Chat** - Conversation history and context management
- **Enterprise Security** - AWS Cognito authentication, encrypted storage
- **Scalable Architecture** - Serverless design with pay-per-use pricing

## 🏗️ Architecture

- **Frontend**: Next.js 14 with TypeScript
- **API**: AWS API Gateway with Lambda functions
- **Search**: AWS Kendra for semantic document search
- **AI**: AWS Bedrock (Claude 3 Haiku)
- **Storage**: S3 for documents, DynamoDB for metadata
- **Auth**: AWS Cognito with custom attributes

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design.

## 💰 Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| Kendra Developer | $810 |
| Lambda & API Gateway | ~$35 |
| Bedrock (Haiku) | ~$30 |
| Storage & Database | ~$50 |
| **Total** | **~$925/month** |

## 🚦 Deployment

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for:
- Step-by-step deployment instructions
- Environment configuration
- Multi-tenant setup
- Production checklist

## 🔧 Key Scripts

```bash
# Re-index documents with tenant isolation
cd scripts
python3 reindex-all-documents.py

# Test multi-tenant isolation
python3 test_multi_tenancy.py

# Query documents via CLI
python3 strata-utils.py query "What is the quorum for AGM?"
```

## 📂 Project Structure

```
stratagpt-project/
├── frontend/           # Next.js application
├── backend/           
│   └── lambdas/       # Lambda functions
├── infrastructure/
│   └── cdk/           # AWS CDK infrastructure
├── scripts/           # Utility scripts
└── docs/              # Documentation
```

## 🔒 Security Features

- ✅ Multi-tenant data isolation via Kendra AttributeFilter
- ✅ IAM policies with least privilege
- ✅ Encrypted data at rest (S3, DynamoDB)
- ✅ CORS domain whitelisting
- ✅ Per-tenant rate limiting
- ✅ AWS Cognito authentication

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📝 License

Proprietary - All rights reserved

---
Built with ❤️ for Australian strata management