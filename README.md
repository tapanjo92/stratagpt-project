# Australian Strata GPT

A specialized document Q&A service for Australian strata management, providing accurate answers with legal-grade citations from strata documents.

## 🎯 Current Status
- ✅ **Phase 1.1-1.4**: Infrastructure, ingestion pipeline, and vector storage complete
- ✅ **Phase 2.1**: RAG implementation with Kendra and Bedrock complete
- 🚧 **Next**: Phase 2.2 - Chat API implementation

## 🚀 Quick Start

```bash
# Install dependencies
cd infrastructure/cdk
npm install

# Deploy infrastructure
npm run deploy
```

## 📋 Features

- **Document Processing**: OCR for PDFs, DOCX, and images using AWS Textract
- **PII Protection**: Automatic redaction of Australian personal information
- **Semantic Search**: Dual search with AWS Kendra and OpenSearch k-NN
- **RAG System**: Context-aware answers using Claude 3 on Bedrock
- **Multi-tenancy**: Secure tenant isolation
- **Scalability**: Serverless architecture with AWS Lambda
- **Evaluation**: Built-in testing harness with 20+ strata-specific questions

## 🏗️ Architecture

```
Documents → S3 → Textract → Chunking → Embeddings → OpenSearch
                     ↓                                      ↓
                  Kendra ← ← ← ← ← RAG Query → → → →  Bedrock (Claude 3)
                                       ↓
                                  Q&A Response
```

## 📁 Project Structure

```
strata-project/
├── backend/               # Lambda functions
│   └── lambdas/
│       ├── textract-processor/    # OCR processing
│       ├── chunk-sanitizer/       # Text chunking & PII removal
│       ├── embeddings-generator/  # Vector embeddings
│       ├── rag-query/            # RAG query handler
│       └── rag-evaluation/       # Evaluation harness
├── infrastructure/        # AWS CDK infrastructure
│   └── cdk/
│       └── stacks/
├── scripts/              # Utility scripts
│   ├── upload-sample-documents.sh
│   ├── trigger-kendra-sync.py
│   ├── run-evaluation.py
│   └── strata-utils.py
├── tests/                # Unit and integration tests
├── docs/                 # Documentation
└── data/                 # Sample strata documents
```

## 🧪 Testing

```bash
# Run unit tests
cd tests
pytest unit/ -v

# Run integration tests
pytest integration/ -v

# Run RAG evaluation
cd scripts
python3 run-evaluation.py

# Quick RAG test
python3 strata-utils.py query "What is the quorum for an AGM?"
```

## 📊 Monitoring

- CloudWatch Dashboard: `strata-ingestion-pipeline`
- Metrics: Document processing, latency, errors
- Alarms: Failed executions, DLQ messages

## 📚 Documentation

- [Development Guide](docs/DEVELOPMENT.md)
- [Infrastructure README](infrastructure/README.md)
- [Delivery Phases](docs/delivery-phases.md)
- [Scripts README](scripts/README.md)
- [Phase 2.1 Test Results](PHASE_2_1_TEST_RESULTS.md)

## 🔒 Security

- All data encrypted at rest and in transit
- PII automatically redacted
- IAM roles follow least privilege
- VPC isolation for sensitive services

## 🤝 Contributing

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for contribution guidelines.

## 📄 License

[Your License Here]