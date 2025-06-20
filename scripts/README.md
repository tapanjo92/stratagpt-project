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

### 4. `strata-utils.py`
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
- Currently using tenant_id='ALL' as a workaround for Kendra metadata filtering issue
- Evaluation results are saved with timestamps for tracking improvements