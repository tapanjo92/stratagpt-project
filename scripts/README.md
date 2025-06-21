# Utility Scripts

Essential scripts for managing and testing the StratAGPT system.

## Production Scripts

### `reindex-all-documents.py`
Re-indexes all documents in S3 with proper tenant isolation attributes.
- **When to use**: After initial deployment or when fixing tenant isolation
- **Usage**: `python3 reindex-all-documents.py`

### `strata-utils.py`
Main utility for querying documents and checking system status.
- **Usage**: 
  ```bash
  python3 strata-utils.py query "What is the quorum?"
  python3 strata-utils.py status
  ```

## Testing Scripts

### `test_multi_tenancy.py`
Verifies multi-tenant isolation is working correctly.
- **Usage**: `python3 test_multi_tenancy.py`
- **Expected**: Each tenant sees only their own documents

### `run-evaluation.py`
Runs the full evaluation suite with test questions.
- **Usage**: `python3 run-evaluation.py`
- **Note**: May hit rate limits if run frequently

### `test-api-load.py`
Load testing for the API endpoints.
- **Usage**: `python3 test-api-load.py --url <api-url> --concurrent 10`

## Prerequisites

- Python 3.8+
- boto3 package (`pip install boto3`)
- AWS credentials configured
- Appropriate IAM permissions

## Environment Variables

- `AWS_REGION`: Default is `ap-south-1`
- Standard AWS credential environment variables

## Removed Scripts

The following scripts were removed as they're no longer needed:
- `test-opensearch.py` - Not using OpenSearch
- `ingest-to-kendra.py` - Replaced by custom ingestion Lambda
- `trigger-kendra-sync.py` - Using custom ingestion instead of S3 sync
- `upload-sample-documents.sh` - Use AWS CLI directly
- `verify_isolation.py` - Temporary testing script