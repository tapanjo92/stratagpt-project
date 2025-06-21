# Phase 2.2: Chat API Development Plan

## Overview
Phase 2.2 focuses on building a production-ready Chat API that leverages the RAG system from Phase 2.1. The API will support streaming responses, conversation history, and handle concurrent requests.

## Architecture Design

### API Structure
```
API Gateway (REST)
    └── /v1
        ├── /chat
        │   ├── POST /conversations - Create new conversation
        │   ├── POST /conversations/{id}/messages - Send message
        │   ├── GET /conversations/{id} - Get conversation history
        │   └── DELETE /conversations/{id} - Delete conversation
        ├── /health - Health check endpoint
        └── /status - System status

Lambda Functions:
- ChatResolverFunction - Main chat handler with streaming
- ConversationManagerFunction - Manage conversation state
```

### Data Models

#### DynamoDB Tables
1. **Conversations Table**
   - PK: tenant_id
   - SK: conversation_id
   - Attributes: created_at, updated_at, user_id, title, status

2. **Messages Table**
   - PK: conversation_id
   - SK: timestamp#message_id
   - Attributes: role (user/assistant), content, citations, tokens_used

### Technical Implementation

#### 1. Streaming Architecture
- Use Lambda response streaming for real-time responses
- Implement Server-Sent Events (SSE) format
- Stream tokens as they're generated from Bedrock

#### 2. Session Management
- JWT tokens for authentication (prepare for Cognito in Phase 2.4)
- Session state in DynamoDB with TTL
- Conversation context window management (last 10 messages)

#### 3. API Features
- Request/response validation with JSON schemas
- API versioning via path (/v1/)
- Rate limiting per tenant
- Request ID tracking for debugging

## Implementation Steps

### Step 1: Create API Infrastructure
- New API Gateway REST API
- Lambda functions with streaming enabled
- DynamoDB tables for conversations

### Step 2: Implement Core Chat Logic
- Extend RAG query handler for conversation context
- Add streaming response capability
- Implement message history retrieval

### Step 3: Add Conversation Management
- Create/retrieve/delete conversations
- Message persistence
- Context window management

### Step 4: API Security & Validation
- Request/response schemas
- Input validation
- Error handling
- CORS configuration

### Step 5: Testing & Documentation
- Postman collection
- Load testing with 100 concurrent users
- API documentation

## Success Metrics
- ✓ SSE streaming working end-to-end
- ✓ API handles 100 concurrent requests
- ✓ JWT token validation implemented
- ✓ <500ms latency for message initiation
- ✓ Conversation history properly maintained

## Integration with Phase 2.1
- Reuse RAG query Lambda as base
- Extend with conversation context
- Maintain tenant isolation
- Use same Kendra/Bedrock configuration

## Preparation for Future Phases
- JWT structure compatible with Cognito (Phase 2.4)
- API design supports frontend integration (Phase 2.3)
- Scalable architecture for multi-tenancy (Phase 3)

## Estimated Timeline
- Infrastructure setup: 1 day
- Core implementation: 2 days
- Testing and refinement: 2 days
- Documentation: 1 day
- **Total: 6 days (Week 6)**