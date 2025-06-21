import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
bedrock_runtime = boto3.client('bedrock-runtime')

# Environment variables
CONVERSATIONS_TABLE = os.environ['CONVERSATIONS_TABLE']
MESSAGES_TABLE = os.environ['MESSAGES_TABLE']
RAG_FUNCTION_ARN = os.environ['RAG_FUNCTION_ARN']
KENDRA_INDEX_ID = os.environ['KENDRA_INDEX_ID']

# DynamoDB tables
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
messages_table = dynamodb.Table(MESSAGES_TABLE)

class ChatResolver:
    def __init__(self):
        self.model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        self.max_tokens = 4096
        self.temperature = 0.7
        self.context_window = 10  # Number of previous messages to include

    def get_conversation_context(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieve recent messages from conversation history"""
        try:
            response = messages_table.query(
                KeyConditionExpression='conversation_id = :conv_id',
                ExpressionAttributeValues={':conv_id': conversation_id},
                ScanIndexForward=False,  # Most recent first
                Limit=self.context_window
            )
            
            # Reverse to get chronological order
            messages = response.get('Items', [])
            messages.reverse()
            
            return messages
        except ClientError as e:
            print(f"Error retrieving conversation context: {e}")
            return []

    def save_message(self, conversation_id: str, tenant_id: str, role: str, 
                    content: str, citations: Optional[List] = None) -> str:
        """Save a message to the messages table"""
        timestamp = datetime.utcnow().isoformat()
        message_id = str(uuid.uuid4())
        timestamp_message_id = f"{timestamp}#{message_id}"
        
        item = {
            'conversation_id': conversation_id,
            'timestamp_message_id': timestamp_message_id,
            'tenant_id': tenant_id,
            'message_id': message_id,
            'timestamp': timestamp,
            'role': role,
            'content': content,
            'created_at': timestamp
        }
        
        if citations:
            item['citations'] = citations
        
        try:
            messages_table.put_item(Item=item)
            return message_id
        except ClientError as e:
            print(f"Error saving message: {e}")
            raise

    def update_conversation(self, tenant_id: str, conversation_id: str):
        """Update conversation's last activity timestamp"""
        try:
            conversations_table.update_item(
                Key={
                    'tenant_id': tenant_id,
                    'conversation_id': conversation_id
                },
                UpdateExpression='SET updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )
        except ClientError as e:
            print(f"Error updating conversation: {e}")

    def invoke_rag_query(self, question: str, tenant_id: str) -> Dict[str, Any]:
        """Invoke the RAG query Lambda function"""
        try:
            payload = {
                'question': question,
                'tenant_id': tenant_id
            }
            
            response = lambda_client.invoke(
                FunctionName=RAG_FUNCTION_ARN,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            if 'body' in result:
                return json.loads(result['body'])
            return result
            
        except ClientError as e:
            print(f"Error invoking RAG query: {e}")
            return {
                'answer': "I'm sorry, I couldn't retrieve information to answer your question.",
                'citations': []
            }

    def build_prompt_with_context(self, question: str, context_messages: List[Dict], 
                                 rag_response: Dict) -> str:
        """Build the prompt including conversation context and RAG response"""
        prompt_parts = []
        
        # System instruction
        prompt_parts.append("""You are an AI assistant specializing in Australian strata management. 
You help strata managers, committee members, and lot owners understand strata laws, 
by-laws, and best practices. Always be helpful, accurate, and cite relevant information.""")
        
        # Add conversation context
        if context_messages:
            prompt_parts.append("\nPrevious conversation:")
            for msg in context_messages:
                role = "Human" if msg['role'] == 'user' else "Assistant"
                prompt_parts.append(f"{role}: {msg['content']}")
        
        # Add RAG context
        if rag_response.get('answer'):
            prompt_parts.append(f"\nRelevant information from documents:\n{rag_response['answer']}")
        
        # Add current question
        prompt_parts.append(f"\nHuman: {question}")
        prompt_parts.append("\nAssistant:")
        
        return "\n".join(prompt_parts)

    def generate_response(self, prompt: str, stream: bool = False) -> Dict[str, Any]:
        """Generate response using Bedrock"""
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
        
        try:
            if stream:
                response = bedrock_runtime.invoke_model_with_response_stream(
                    modelId=self.model_id,
                    body=body
                )
                return self.handle_streaming_response(response)
            else:
                response = bedrock_runtime.invoke_model(
                    modelId=self.model_id,
                    body=body,
                    contentType='application/json'
                )
                
                response_body = json.loads(response['body'].read())
                return {
                    'content': response_body['content'][0]['text'],
                    'usage': response_body.get('usage', {})
                }
                
        except ClientError as e:
            print(f"Error generating response: {e}")
            raise

    def handle_streaming_response(self, response) -> Dict[str, Any]:
        """Handle streaming response from Bedrock"""
        stream = response.get('body')
        content_parts = []
        
        if stream:
            for event in stream:
                chunk = event.get('chunk')
                if chunk:
                    chunk_data = json.loads(chunk.get('bytes').decode())
                    if chunk_data['type'] == 'content_block_delta':
                        content_parts.append(chunk_data['delta']['text'])
        
        return {
            'content': ''.join(content_parts),
            'stream': True
        }

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for chat messages"""
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        conversation_id = event.get('conversationId')
        tenant_id = event.get('tenantId')
        user_id = event.get('userId', 'anonymous')
        body = event.get('body', {})
        
        if isinstance(body, str):
            body = json.loads(body)
        
        message = body.get('message')
        stream = body.get('stream', False)
        
        # Validate inputs
        if not all([conversation_id, tenant_id, message]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'BadRequest',
                    'message': 'Missing required parameters'
                })
            }
        
        # Initialize chat resolver
        resolver = ChatResolver()
        
        # Save user message
        user_message_id = resolver.save_message(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role='user',
            content=message
        )
        
        # Get conversation context
        context_messages = resolver.get_conversation_context(conversation_id)
        
        # Invoke RAG query for relevant information
        rag_response = resolver.invoke_rag_query(message, tenant_id)
        
        # Build prompt with context
        prompt = resolver.build_prompt_with_context(
            question=message,
            context_messages=context_messages[:-1],  # Exclude the message we just saved
            rag_response=rag_response
        )
        
        # Generate response
        start_time = time.time()
        response = resolver.generate_response(prompt, stream=stream)
        generation_time = int((time.time() - start_time) * 1000)
        
        # Save assistant response
        assistant_message_id = resolver.save_message(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role='assistant',
            content=response['content'],
            citations=rag_response.get('citations', [])
        )
        
        # Update conversation timestamp
        resolver.update_conversation(tenant_id, conversation_id)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'conversation_id': conversation_id,
                'message_id': assistant_message_id,
                'content': response['content'],
                'citations': rag_response.get('citations', []),
                'generation_time_ms': generation_time,
                'usage': response.get('usage', {})
            })
        }
        
    except Exception as e:
        print(f"Error in handler: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'InternalServerError',
                'message': str(e)
            })
        }