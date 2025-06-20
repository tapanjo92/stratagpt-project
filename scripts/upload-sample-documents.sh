#!/bin/bash
# Script to upload sample strata documents to S3 for Kendra indexing

BUCKET_NAME="strata-documents-809555764832-ap-south-1"
TENANT_ID="test-tenant"
AWS_REGION="ap-south-1"

echo "Uploading sample strata documents..."

# Convert JSON to text files and upload
for file in /root/strata-project/data/sample-strata-documents/*.json; do
    filename=$(basename "$file" .json)
    
    # Extract content from JSON and create text file
    jq -r '.content' "$file" > "/tmp/${filename}.txt"
    
    # Extract metadata
    title=$(jq -r '.title' "$file")
    doc_type=$(jq -r '.document_type' "$file")
    
    # Upload to S3 with metadata
    aws s3 cp "/tmp/${filename}.txt" \
        "s3://${BUCKET_NAME}/${TENANT_ID}/documents/${filename}.txt" \
        --region ${AWS_REGION} \
        --metadata "tenant_id=${TENANT_ID},document_type=${doc_type},title=${title}"
    
    echo "Uploaded: ${filename}.txt"
done

# Create metadata files for Kendra
echo "Creating Kendra metadata files..."

for file in /root/strata-project/data/sample-strata-documents/*.json; do
    filename=$(basename "$file" .json)
    
    # Create Kendra metadata JSON  
    export BUCKET_NAME
    jq --arg tenant_id "$TENANT_ID" --arg bucket "$BUCKET_NAME" --arg fname "$filename" '{
        "DocumentId": ($fname + ".txt"),
        "Attributes": {
            "tenant_id": $tenant_id,
            "document_type": .document_type,
            "_category": .document_type,
            "_created_at": (now | strftime("%Y-%m-%dT%H:%M:%SZ")),
            "_source_uri": ("s3://" + $bucket + "/" + $tenant_id + "/documents/" + $fname + ".txt")
        }
    }' "$file" > "/tmp/${filename}.metadata.json"
    
    # Upload metadata
    aws s3 cp "/tmp/${filename}.metadata.json" \
        "s3://${BUCKET_NAME}/${TENANT_ID}/metadata/${filename}.txt.metadata.json" \
        --region ${AWS_REGION}
    
    echo "Uploaded metadata: ${filename}.metadata.json"
done

echo "Sample document upload complete!"
echo "Documents are ready for Kendra indexing."