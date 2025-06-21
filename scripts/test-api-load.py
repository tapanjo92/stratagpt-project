#!/usr/bin/env python3
"""
Load test script for Australian Strata GPT Chat API
Tests concurrent API requests to ensure performance under load
"""

import asyncio
import aiohttp
import json
import time
import statistics
from datetime import datetime
import argparse
import uuid

class APILoadTester:
    def __init__(self, base_url, tenant_id="test-tenant"):
        self.base_url = base_url.rstrip('/')
        self.tenant_id = tenant_id
        self.results = []
        
    async def create_conversation(self, session):
        """Create a new conversation"""
        url = f"{self.base_url}/v1/chat/conversations"
        headers = {
            "X-Tenant-Id": self.tenant_id,
            "Content-Type": "application/json"
        }
        data = {
            "title": f"Load Test Conversation {datetime.now().isoformat()}",
            "metadata": {"test_type": "load_test"}
        }
        
        async with session.post(url, json=data, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                return result.get('conversation_id')
            else:
                print(f"Failed to create conversation: {response.status}")
                return None
    
    async def send_message(self, session, conversation_id, message):
        """Send a message to a conversation"""
        url = f"{self.base_url}/v1/chat/conversations/{conversation_id}/messages"
        headers = {
            "X-Tenant-Id": self.tenant_id,
            "Content-Type": "application/json"
        }
        data = {
            "message": message,
            "stream": False
        }
        
        start_time = time.time()
        try:
            async with session.post(url, json=data, headers=headers) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                
                result = {
                    "status": response.status,
                    "response_time_ms": response_time,
                    "timestamp": datetime.now().isoformat()
                }
                
                if response.status == 200:
                    body = await response.json()
                    result["generation_time_ms"] = body.get("generation_time_ms", 0)
                    result["success"] = True
                else:
                    result["success"] = False
                    result["error"] = await response.text()
                
                return result
                
        except Exception as e:
            end_time = time.time()
            return {
                "status": 0,
                "response_time_ms": (end_time - start_time) * 1000,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    async def test_concurrent_requests(self, num_requests, messages):
        """Test concurrent API requests"""
        print(f"\nStarting load test with {num_requests} concurrent requests...")
        print(f"Target API: {self.base_url}")
        print(f"Tenant ID: {self.tenant_id}")
        print("-" * 60)
        
        async with aiohttp.ClientSession() as session:
            # First, create conversations for each request
            print("Creating conversations...")
            conversations = []
            for i in range(num_requests):
                conv_id = await self.create_conversation(session)
                if conv_id:
                    conversations.append(conv_id)
                    
            if len(conversations) < num_requests:
                print(f"Warning: Only created {len(conversations)} conversations")
                num_requests = len(conversations)
            
            # Now send messages concurrently
            print(f"\nSending {num_requests} messages concurrently...")
            tasks = []
            for i in range(num_requests):
                message = messages[i % len(messages)]
                task = self.send_message(session, conversations[i], message)
                tasks.append(task)
            
            # Execute all requests concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            # Store results
            self.results = results
            
            # Print summary
            self.print_summary(total_time)
    
    def print_summary(self, total_time):
        """Print test results summary"""
        successful = [r for r in self.results if r.get("success", False)]
        failed = [r for r in self.results if not r.get("success", False)]
        
        print("\n" + "=" * 60)
        print("LOAD TEST SUMMARY")
        print("=" * 60)
        
        print(f"\nTotal Requests: {len(self.results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        print(f"Success Rate: {len(successful)/len(self.results)*100:.1f}%")
        print(f"Total Test Duration: {total_time:.2f} seconds")
        
        if successful:
            response_times = [r["response_time_ms"] for r in successful]
            generation_times = [r.get("generation_time_ms", 0) for r in successful if r.get("generation_time_ms")]
            
            print(f"\nResponse Time Statistics (ms):")
            print(f"  Min: {min(response_times):.0f}")
            print(f"  Max: {max(response_times):.0f}")
            print(f"  Mean: {statistics.mean(response_times):.0f}")
            print(f"  Median: {statistics.median(response_times):.0f}")
            if len(response_times) > 1:
                print(f"  Std Dev: {statistics.stdev(response_times):.0f}")
            
            if generation_times:
                print(f"\nGeneration Time Statistics (ms):")
                print(f"  Min: {min(generation_times):.0f}")
                print(f"  Max: {max(generation_times):.0f}")
                print(f"  Mean: {statistics.mean(generation_times):.0f}")
        
        if failed:
            print(f"\nFailed Requests:")
            for r in failed[:5]:  # Show first 5 failures
                print(f"  - Status: {r['status']}, Error: {r.get('error', 'Unknown')}")
            if len(failed) > 5:
                print(f"  ... and {len(failed) - 5} more")
        
        # Check if meeting performance targets
        print("\n" + "-" * 60)
        print("Performance Target Check:")
        if successful:
            avg_response_time = statistics.mean(response_times)
            if avg_response_time < 3000:
                print("✅ Average response time < 3 seconds")
            else:
                print("❌ Average response time exceeds 3 seconds")
        
        if len(successful) == len(self.results):
            print("✅ 100% success rate")
        elif len(successful) / len(self.results) >= 0.95:
            print("✅ >95% success rate")
        else:
            print("❌ Success rate below 95%")

def main():
    parser = argparse.ArgumentParser(description='Load test the Strata GPT Chat API')
    parser.add_argument('--url', required=True, help='Base URL of the API')
    parser.add_argument('--concurrent', type=int, default=100, help='Number of concurrent requests')
    parser.add_argument('--tenant', default='test-tenant', help='Tenant ID to use')
    
    args = parser.parse_args()
    
    # Test messages to use
    test_messages = [
        "What is the quorum for an AGM?",
        "How many units are in the building?",
        "What are the pet by-laws?",
        "Explain the levy collection process",
        "What are the committee's responsibilities?",
        "How do I dispute a levy?",
        "What maintenance is the owners corporation responsible for?",
        "Can I renovate my bathroom?",
        "What are the parking rules?",
        "How often should AGMs be held?"
    ]
    
    # Create tester and run
    tester = APILoadTester(args.url, args.tenant)
    
    # Run the async test
    asyncio.run(tester.test_concurrent_requests(args.concurrent, test_messages))

if __name__ == "__main__":
    main()