# Australian Strata GPT

A specialized document Q&A service for Australian strata management, providing accurate answers with legal-grade citations from strata documents.

## 🚀 Quick Start

```bash
# Install dependencies
cd infrastructure/cdk
npm install

# Deploy infrastructure
npm run deploy
```

## 📋 Features

- **Document Processing**: OCR for PDFs, DOCX, and images
- **PII Protection**: Automatic redaction of Australian personal information
- **Vector Search**: Semantic search using OpenSearch k-NN
- **Multi-tenancy**: Secure tenant isolation
- **Scalability**: Serverless architecture with AWS Lambda

## 🏗️ Architecture

```
Documents → S3 → Textract → Chunking → Embeddings → OpenSearch → Q&A API
```

## 📁 Project Structure

```
strata-project/
├── backend/               # Lambda functions
│   └── lambdas/
│       ├── textract-processor/
│       ├── chunk-sanitizer/
│       └── embeddings-generator/
├── infrastructure/        # AWS CDK infrastructure
│   └── cdk/
│       └── stacks/
├── tests/                # Unit and integration tests
├── docs/                 # Documentation
└── delivery-phases.md    # Detailed project roadmap
```

## 🧪 Testing

```bash
# Run unit tests
cd tests
pytest unit/ -v

# Run integration tests
pytest integration/ -v
```

## 📊 Monitoring

- CloudWatch Dashboard: `strata-ingestion-pipeline`
- Metrics: Document processing, latency, errors
- Alarms: Failed executions, DLQ messages

## 📚 Documentation

- [Development Guide](docs/DEVELOPMENT.md)
- [Infrastructure README](infrastructure/README.md)
- [Delivery Phases](delivery-phases.md)

## 🔒 Security

- All data encrypted at rest and in transit
- PII automatically redacted
- IAM roles follow least privilege
- VPC isolation for sensitive services

## 🤝 Contributing

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for contribution guidelines.

## 📄 License

[Your License Here]