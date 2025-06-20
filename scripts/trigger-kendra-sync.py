#!/usr/bin/env python3
"""Script to manually trigger Kendra data source sync"""

import boto3
import json
import time

# Initialize clients
kendra = boto3.client('kendra', region_name='ap-south-1')
ssm = boto3.client('ssm', region_name='ap-south-1')

# Get Kendra index ID
try:
    response = ssm.get_parameter(Name='/strata-gpt/kendra-index-id')
    KENDRA_INDEX_ID = response['Parameter']['Value']
    print(f"Using Kendra Index ID from SSM: {KENDRA_INDEX_ID}")
except:
    KENDRA_INDEX_ID = '16a4c50d-197f-4e7c-9ffa-476b42e0fcf2'
    print(f"Using hardcoded Kendra Index ID: {KENDRA_INDEX_ID}")

def trigger_sync():
    """Trigger a manual sync of all data sources"""
    
    try:
        # List data sources
        response = kendra.list_data_sources(IndexId=KENDRA_INDEX_ID)
        data_sources = response.get('SummaryItems', [])
        
        print(f"Found {len(data_sources)} data sources")
        
        for ds in data_sources:
            print(f"\nTriggering sync for: {ds['Name']} (ID: {ds['Id']})")
            
            try:
                # Start sync job
                sync_response = kendra.start_data_source_sync_job(
                    Id=ds['Id'],
                    IndexId=KENDRA_INDEX_ID
                )
                
                execution_id = sync_response.get('ExecutionId')
                print(f"Sync job started with execution ID: {execution_id}")
                
                # Wait and check status
                print("Waiting for sync to complete...")
                max_wait = 300  # 5 minutes
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    # Get sync job status
                    status_response = kendra.list_data_source_sync_jobs(
                        Id=ds['Id'],
                        IndexId=KENDRA_INDEX_ID,
                        MaxResults=1
                    )
                    
                    if status_response.get('History'):
                        latest_job = status_response['History'][0]
                        status = latest_job.get('Status')
                        
                        print(f"  Status: {status}")
                        
                        if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
                            if status == 'SUCCEEDED':
                                metrics = latest_job.get('Metrics', {})
                                print(f"  Sync completed successfully!")
                                print(f"  Documents: Added={metrics.get('DocumentsAdded', 0)}, "
                                      f"Modified={metrics.get('DocumentsModified', 0)}, "
                                      f"Deleted={metrics.get('DocumentsDeleted', 0)}, "
                                      f"Failed={metrics.get('DocumentsFailed', 0)}")
                            else:
                                print(f"  Sync {status}")
                                if latest_job.get('ErrorMessage'):
                                    print(f"  Error: {latest_job['ErrorMessage']}")
                            break
                    
                    time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"  Error triggering sync: {str(e)}")
                
    except Exception as e:
        print(f"Error: {str(e)}")

def check_document_count():
    """Check how many documents are indexed"""
    print("\nChecking indexed document count...")
    
    try:
        # Run a simple query to get total document count
        response = kendra.query(
            IndexId=KENDRA_INDEX_ID,
            QueryText='*',  # Match all documents
            PageSize=1
        )
        
        total_docs = response.get('TotalNumberOfResults', 0)
        print(f"Total documents indexed: {total_docs}")
        
    except Exception as e:
        print(f"Error checking document count: {str(e)}")

if __name__ == '__main__':
    print("Kendra Manual Sync Trigger")
    print("==========================\n")
    
    trigger_sync()
    print("\nWaiting 30 seconds before checking document count...")
    time.sleep(30)
    check_document_count()