# Australian Strata GPT

A specialized document Q&A service for Australian strata management, providing accurate answers with legal-grade citations from strata documents.

## 🎯 Current Status
- ✅ **Phase 1.1-1.4**: Infrastructure, ingestion pipeline, and vector storage complete
- ✅ **Phase 2.1**: RAG implementation with Kendra and Bedrock complete
- ✅ **Phase 2.2**: Chat API with conversation management complete
- ✅ **Phase 2.3**: Frontend application with Next.js complete
- ✅ **Phase 2.4**: Authentication with AWS Cognito complete
- 🚧 **Next**: Phase 3 - Multi-tenancy, Billing, and Admin Portal

## 🚀 Quick Start

### Prerequisites
- AWS Account with appropriate permissions
- Node.js 18+ and npm
- Python 3.11+
- Docker (for CDK Lambda deployment)
- AWS CLI configured

### Backend Deployment
```bash
# Install CDK dependencies
cd infrastructure/cdk
npm install

# Deploy all stacks
npm run build
cdk deploy --all --require-approval never
```

### Frontend Setup
```bash
# Install frontend dependencies
cd frontend
npm install

# Create environment file
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=https://your-api-gateway-url
NEXT_PUBLIC_AWS_REGION=ap-south-1
NEXT_PUBLIC_USER_POOL_ID=your-user-pool-id
NEXT_PUBLIC_USER_POOL_CLIENT_ID=your-client-id
EOF

# Run development server
npm run dev
```

## 📋 Features

### Core Functionality
- **Document Processing**: OCR for PDFs, DOCX, and images using AWS Textract
- **PII Protection**: Automatic redaction of Australian personal information
- **Semantic Search**: Dual search with AWS Kendra and OpenSearch k-NN
- **RAG System**: Context-aware answers using Claude 3 Haiku on Bedrock (optimized for speed)
- **Multi-tenancy**: Secure tenant isolation with proper data boundaries
- **Chat Interface**: Real-time conversation with context retention
- **Authentication**: AWS Cognito with role-based access control

### Technical Features
- **Serverless Architecture**: AWS Lambda for all compute
- **Event-Driven**: Automatic document processing via EventBridge
- **Scalable**: Auto-scaling for all components
- **Monitored**: CloudWatch dashboards and alarms
- **Secure**: End-to-end encryption, VPC isolation

## 🏗️ Architecture

### System Overview
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Next.js   │────▶│ API Gateway │────▶│   Lambda    │
│  Frontend   │     │   + Auth    │     │  Functions  │
└─────────────┘     └─────────────┘     └─────────────┘
                            │                    │
                            ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Cognito   │     │  DynamoDB   │
                    │ User Pools  │     │   Tables    │
                    └─────────────┘     └─────────────┘
                                               │
                    ┌─────────────┐            ▼
                    │   Kendra    │◀────┌─────────────┐
                    │    Index    │     │     RAG     │
                    └─────────────┘     │   System    │
                            ▲           └─────────────┘
                            │                    │
                    ┌─────────────┐     ┌─────────────┐
                    │ S3 Buckets  │     │   Bedrock   │
                    │ (Documents) │     │ Claude 3 H  │
                    └─────────────┘     └─────────────┘
```

### Data Flow
1. **Document Ingestion**: S3 → Textract → Chunking → Embeddings → Storage
2. **Query Processing**: User → API → RAG → Kendra/OpenSearch → Bedrock → Response
3. **Authentication**: Frontend → Cognito → JWT → API Authorization

## 📁 Project Structure

```
strata-project/
├── frontend/              # Next.js frontend application
│   ├── src/
│   │   ├── app/          # App router pages
│   │   ├── components/   # React components
│   │   ├── contexts/     # React contexts (auth)
│   │   ├── lib/          # Utilities and API client
│   │   └── types/        # TypeScript definitions
│   └── public/           # Static assets
├── backend/              # Lambda functions
│   └── lambdas/
│       ├── textract-processor/      # OCR processing
│       ├── chunk-sanitizer/         # Text chunking & PII removal
│       ├── embeddings-generator/    # Vector embeddings
│       ├── rag-query/              # RAG query handler
│       ├── rag-evaluation/         # Evaluation harness
│       ├── kendra-custom-ingest/   # Custom Kendra ingestion
│       ├── chat-resolver/          # Chat message handler
│       └── conversation-manager/   # Conversation CRUD
├── infrastructure/       # AWS CDK infrastructure
│   └── cdk/
│       └── stacks/
│           ├── network-stack.ts    # VPC configuration
│           ├── storage-stack.ts    # S3 and DynamoDB
│           ├── auth-stack.ts       # Cognito setup
│           ├── api-stack.ts        # API Gateway + Lambdas
│           └── rag-stack.ts        # Kendra and RAG
├── scripts/             # Utility scripts
│   ├── strata-utils.py           # CLI for testing
│   ├── run-evaluation.py         # Run test suite
│   ├── test-api-load.py         # Load testing
│   └── ingest-to-kendra.py      # Manual ingestion
├── tests/               # Unit and integration tests
├── docs/                # Documentation
│   ├── delivery-phases.md        # Project roadmap
│   └── DEVELOPMENT.md           # Dev guide
└── data/                # Sample strata documents
```

## 🧪 Testing

### Backend Testing
```bash
# Run unit tests
cd tests
pytest unit/ -v

# Test RAG query
cd scripts
python3 strata-utils.py query "What is the quorum for an AGM?" --tenant test-tenant

# Run evaluation suite
python3 run-evaluation.py

# Load test API (after deployment)
python3 test-api-load.py --url https://your-api-url --concurrent 100
```

### Frontend Testing
```bash
cd frontend

# Run Storybook for component testing
npm run storybook

# Run development server
npm run dev

# Build for production
npm run build
```

## 📊 Monitoring & Operations

### CloudWatch Dashboards
- **Ingestion Pipeline**: Document processing metrics
- **API Performance**: Request latency, errors
- **Lambda Functions**: Invocations, duration, errors

### Key Metrics
- Document processing time: <30s target
- API response time: <3s target (now ~2-3s with Claude 3 Haiku)
- RAG accuracy: 85%+ on test questions
- Tenant isolation: 100% verified

### Alarms
- Failed Lambda executions
- DLQ messages
- API 4xx/5xx errors
- Kendra sync failures

## 🔐 Security & Compliance

### Security Features
- **Encryption**: All data encrypted at rest (S3, DynamoDB) and in transit (TLS)
- **Authentication**: AWS Cognito with MFA support
- **Authorization**: Role-based access control (Owner, Manager, Admin)
- **Tenant Isolation**: Strict data boundaries enforced at all levels
- **PII Protection**: Automatic redaction of personal information
- **Audit Trail**: All actions logged to CloudWatch

### Compliance
- Data residency in Australia (ap-south-1)
- 7-year retention capability for audit logs
- GDPR/Privacy Act considerations in design

## 📚 Documentation

### Implementation Guides
- [Phase 2.1 Analysis](PHASE_2_1_ANALYSIS.md) - RAG implementation details
- [Phase 2.2 Implementation](PHASE_2_2_IMPLEMENTATION.md) - API development
- [Phase 2.3 & 2.4 Implementation](PHASE_2_3_2_4_IMPLEMENTATION.md) - Frontend & Auth
- [Deployment Summary](DEPLOYMENT_SUMMARY.md) - Current deployment details

### Technical Docs
- [Custom Ingestion Implementation](CUSTOM_INGESTION_IMPLEMENTATION.md) - Kendra integration
- [Tenant Isolation Status](TENANT_ISOLATION_STATUS.md) - Multi-tenancy details
- [Infrastructure README](infrastructure/README.md) - CDK details
- [Scripts README](scripts/README.md) - Utility scripts guide

### API Documentation
- API Endpoint: See DEPLOYMENT_SUMMARY.md
- Postman Collection: `Australian-Strata-GPT-API.postman_collection.json`

## 🚦 Known Issues & Limitations

1. **Performance**: Average response time ~4.4s (target <3s)
2. **Streaming**: Lambda doesn't support true streaming yet
3. **File Upload**: S3 presigned URL integration pending
4. **Search**: Limited to English language
5. **Scale**: Kendra Developer Edition has document limits

## 🛣️ Roadmap

### Phase 3.1: Multi-tenant Data Architecture
- Enhanced tenant management
- Data migration tools
- Backup and recovery

### Phase 3.2: Billing & Subscriptions
- Stripe integration
- Usage metering
- Subscription tiers

### Phase 3.3: Observability & Performance
- Performance optimization (<3s target)
- Enhanced monitoring
- Cost optimization

### Phase 3.4: Admin Dashboard
- Tenant management UI
- Usage analytics
- System health monitoring

## 🤝 Contributing

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for contribution guidelines.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Follow the coding standards
4. Write tests for new features
5. Update documentation
6. Submit a pull request

## 📞 Support

For issues and questions:
- Check existing documentation
- Search closed issues
- Create a new issue with details

## 📄 License

[Your License Here]