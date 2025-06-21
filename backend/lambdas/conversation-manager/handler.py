import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
CONVERSATIONS_TABLE = os.environ['CONVERSATIONS_TABLE']
MESSAGES_TABLE = os.environ['MESSAGES_TABLE']

# DynamoDB tables
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
messages_table = dynamodb.Table(MESSAGES_TABLE)

class ConversationManager:
    def __init__(self):
        self.default_ttl_days = 30  # Conversations expire after 30 days of inactivity

    def create_conversation(self, tenant_id: str, user_id: str, 
                          title: Optional[str] = None, 
                          metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Calculate TTL (30 days from now)
        ttl_timestamp = int((datetime.utcnow() + timedelta(days=self.default_ttl_days)).timestamp())
        
        item = {
            'tenant_id': tenant_id,
            'conversation_id': conversation_id,
            'user_id': user_id,
            'title': title or f"Conversation {timestamp[:10]}",
            'status': 'active',
            'created_at': timestamp,
            'updated_at': timestamp,
            'ttl': ttl_timestamp,
            'message_count': 0
        }
        
        if metadata:
            item['metadata'] = metadata
        
        try:
            conversations_table.put_item(Item=item)
            return {
                'conversation_id': conversation_id,
                'title': item['title'],
                'created_at': timestamp,
                'status': 'active'
            }
        except ClientError as e:
            print(f"Error creating conversation: {e}")
            raise

    def get_conversation(self, tenant_id: str, conversation_id: str, 
                        user_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation details with messages"""
        try:
            # Get conversation metadata
            response = conversations_table.get_item(
                Key={
                    'tenant_id': tenant_id,
                    'conversation_id': conversation_id
                }
            )
            
            conversation = response.get('Item')
            if not conversation:
                return None
            
            # Verify user has access
            if conversation['user_id'] != user_id:
                return None
            
            # Get messages
            messages_response = messages_table.query(
                KeyConditionExpression='conversation_id = :conv_id',
                ExpressionAttributeValues={':conv_id': conversation_id},
                ScanIndexForward=True  # Chronological order
            )
            
            messages = messages_response.get('Items', [])
            
            # Format response
            return {
                'conversation_id': conversation_id,
                'title': conversation['title'],
                'status': conversation['status'],
                'created_at': conversation['created_at'],
                'updated_at': conversation['updated_at'],
                'message_count': len(messages),
                'messages': [
                    {
                        'message_id': msg['message_id'],
                        'role': msg['role'],
                        'content': msg['content'],
                        'timestamp': msg['timestamp'],
                        'citations': msg.get('citations', [])
                    }
                    for msg in messages
                ]
            }
            
        except ClientError as e:
            print(f"Error getting conversation: {e}")
            return None

    def list_conversations(self, tenant_id: str, user_id: str, 
                          limit: int = 20) -> Dict[str, Any]:
        """List user's conversations"""
        try:
            response = conversations_table.query(
                KeyConditionExpression='tenant_id = :tenant_id',
                ExpressionAttributeValues={':tenant_id': tenant_id},
                FilterExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id},
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            
            conversations = response.get('Items', [])
            
            return {
                'conversations': [
                    {
                        'conversation_id': conv['conversation_id'],
                        'title': conv['title'],
                        'status': conv['status'],
                        'created_at': conv['created_at'],
                        'updated_at': conv['updated_at'],
                        'message_count': conv.get('message_count', 0)
                    }
                    for conv in conversations
                ],
                'count': len(conversations),
                'last_evaluated_key': response.get('LastEvaluatedKey')
            }
            
        except ClientError as e:
            print(f"Error listing conversations: {e}")
            return {'conversations': [], 'count': 0}

    def delete_conversation(self, tenant_id: str, conversation_id: str, 
                          user_id: str) -> bool:
        """Delete a conversation and its messages"""
        try:
            # Verify ownership
            conversation = self.get_conversation(tenant_id, conversation_id, user_id)
            if not conversation:
                return False
            
            # Delete all messages
            messages_response = messages_table.query(
                KeyConditionExpression='conversation_id = :conv_id',
                ExpressionAttributeValues={':conv_id': conversation_id},
                ProjectionExpression='conversation_id, timestamp_message_id'
            )
            
            with messages_table.batch_writer() as batch:
                for message in messages_response.get('Items', []):
                    batch.delete_item(
                        Key={
                            'conversation_id': message['conversation_id'],
                            'timestamp_message_id': message['timestamp_message_id']
                        }
                    )
            
            # Delete conversation
            conversations_table.delete_item(
                Key={
                    'tenant_id': tenant_id,
                    'conversation_id': conversation_id
                }
            )
            
            return True
            
        except ClientError as e:
            print(f"Error deleting conversation: {e}")
            return False

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for conversation management"""
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        action = event.get('action')
        tenant_id = event.get('tenantId')
        user_id = event.get('userId', 'anonymous')
        conversation_id = event.get('conversationId')
        body = event.get('body', {})
        
        if isinstance(body, str):
            body = json.loads(body) if body else {}
        
        # Validate tenant_id
        if not tenant_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'BadRequest',
                    'message': 'Missing tenant_id'
                })
            }
        
        # Initialize manager
        manager = ConversationManager()
        
        # Handle different actions
        if action == 'create':
            result = manager.create_conversation(
                tenant_id=tenant_id,
                user_id=user_id,
                title=body.get('title'),
                metadata=body.get('metadata')
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result)
            }
            
        elif action == 'get':
            if not conversation_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'BadRequest',
                        'message': 'Missing conversation_id'
                    })
                }
            
            result = manager.get_conversation(tenant_id, conversation_id, user_id)
            
            if not result:
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': 'NotFound',
                        'message': 'Conversation not found'
                    })
                }
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result)
            }
            
        elif action == 'list':
            result = manager.list_conversations(
                tenant_id=tenant_id,
                user_id=user_id,
                limit=body.get('limit', 20)
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result)
            }
            
        elif action == 'delete':
            if not conversation_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'BadRequest',
                        'message': 'Missing conversation_id'
                    })
                }
            
            success = manager.delete_conversation(tenant_id, conversation_id, user_id)
            
            if not success:
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': 'NotFound',
                        'message': 'Conversation not found or access denied'
                    })
                }
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'message': 'Conversation deleted'})
            }
            
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'BadRequest',
                    'message': f'Invalid action: {action}'
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