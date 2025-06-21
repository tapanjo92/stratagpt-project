# Strata GPT Scripts

This directory contains utility scripts for managing and testing the Strata GPT system.

## Available Scripts

### 1. `upload-sample-documents.sh`
Uploads sample strata documents to S3 for Kendra indexing.

**Usage:**
```bash
./upload-sample-documents.sh
```

**What it does:**
- Converts JSON documents to text format
- Uploads documents to S3 with proper metadata
- Creates Kendra metadata files for document attributes

### 2. `trigger-kendra-sync.py`
Manually triggers Kendra data source synchronization and checks sync status.

**Usage:**
```bash
python3 trigger-kendra-sync.py
```

**Features:**
- Triggers sync for all data sources
- Shows sync progress and results
- Reports document indexing statistics

### 3. `run-evaluation.py`
Runs the evaluation harness to test RAG system performance.

**Usage:**
```bash
# Run full evaluation
python3 run-evaluation.py

# Run only easy questions
python3 run-evaluation.py --subset easy

# Specify different region
python3 run-evaluation.py --region us-east-1
```

**Output:**
- Pass/fail rates
- Average accuracy scores
- Response time metrics
- Detailed results saved to JSON file

### 4. `ingest-to-kendra.py`
Manually triggers custom Kendra ingestion for documents with proper tenant metadata.

**Usage:**
```bash
# Ingest a specific document
python3 ingest-to-kendra.py --key tenant-a/documents/bylaws.pdf

# Ingest all documents for a tenant
python3 ingest-to-kendra.py --tenant tenant-a

# Dry run to see what would be processed
python3 ingest-to-kendra.py --tenant tenant-a --dry-run

# Process all documents in bucket
python3 ingest-to-kendra.py --all
```

**Features:**
- Direct ingestion using batch_put_document API
- Proper tenant_id metadata association
- Progress tracking and error reporting
- Dry-run mode for testing

### 5. `strata-utils.py`
General utility script for common operations.

**Usage:**
```bash
# Query the RAG system
python3 strata-utils.py query "What is the quorum for an AGM?"

# Query with specific tenant
python3 strata-utils.py query "What are the pet by-laws?" --tenant tenant-123

# Check Kendra status
python3 strata-utils.py status

# List CloudFormation outputs
python3 strata-utils.py outputs
```

## Prerequisites

All Python scripts require:
- Python 3.8+
- boto3 package (`pip install boto3`)
- AWS credentials configured
- Appropriate IAM permissions

## Environment Variables

- `AWS_REGION`: Default is `ap-south-1`
- Standard AWS credential environment variables

## Notes

- For production use, always specify tenant_id when querying
- ~~Currently using tenant_id='ALL' as a workaround for Kendra metadata filtering issue~~ **FIXED: Use custom ingestion**
- Evaluation results are saved with timestamps for tracking improvements
- Custom Kendra ingestion (ingest-to-kendra.py) ensures proper tenant isolation
- The ingestion pipeline (Textract/chunking/embeddings) runs automatically via EventBridge