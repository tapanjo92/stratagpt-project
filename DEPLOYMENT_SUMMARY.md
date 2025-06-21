# Australian Strata GPT - Deployment Summary

## Successfully Deployed Stacks

### 1. Auth Stack (StrataGPT-Auth-dev) ✅
- **User Pool ID:** `ap-south-1_JL1MBtqnw`
- **Client ID:** `11scsmdu7iun7cceht5svb9q84`
- **Region:** ap-south-1
- **Features:**
  - Email-based authentication
  - Custom attributes (tenant_id, role)
  - User groups (Admins, Managers, Owners)
  - Pre-signup validation

### 2. API Stack (StrataGPT-API-dev) ✅
- **API Endpoint:** `https://xlq28u9ipe.execute-api.ap-south-1.amazonaws.com/v1/`
- **Features:**
  - REST API with Cognito authorization
  - Chat conversation management
  - Message persistence in DynamoDB
  - Integration with RAG system

## Frontend Configuration

Create a `.env.local` file in the frontend directory with:

```env
NEXT_PUBLIC_API_URL=https://xlq28u9ipe.execute-api.ap-south-1.amazonaws.com
NEXT_PUBLIC_AWS_REGION=ap-south-1
NEXT_PUBLIC_USER_POOL_ID=ap-south-1_JL1MBtqnw
NEXT_PUBLIC_USER_POOL_CLIENT_ID=11scsmdu7iun7cceht5svb9q84
```

## Testing the API

### 1. Health Check (No Auth Required)
```bash
curl https://xlq28u9ipe.execute-api.ap-south-1.amazonaws.com/v1/health
```

### 2. Create Test User
You can create a test user using AWS CLI:
```bash
aws cognito-idp admin-create-user \
  --user-pool-id ap-south-1_JL1MBtqnw \
  --username test@example.com \
  --user-attributes \
    Name=email,Value=test@example.com \
    Name=custom:tenant_id,Value=test-tenant \
    Name=custom:role,Value=owner \
  --temporary-password TempPass123! \
  --message-action SUPPRESS
```

### 3. Add User to Group
```bash
aws cognito-idp admin-add-user-to-group \
  --user-pool-id ap-south-1_JL1MBtqnw \
  --username test@example.com \
  --group-name Owners
```

## Running the Frontend

```bash
cd /root/strata-project/frontend
npm install
npm run dev
```

The application will be available at http://localhost:3000

## API Endpoints

All endpoints except /health require authentication via Cognito JWT token.

- `GET /v1/health` - Health check
- `POST /v1/chat/conversations` - Create conversation
- `GET /v1/chat/conversations/{id}` - Get conversation
- `POST /v1/chat/conversations/{id}/messages` - Send message

## Notes

1. **Authentication:** All API calls (except health) require:
   - `Authorization: Bearer {JWT_TOKEN}` header
   - `X-Tenant-Id: {tenant_id}` header

2. **CORS:** Configured for all origins (update for production)

3. **Rate Limiting:** 100 requests/second with burst of 200

4. **Lambda Timeouts:**
   - Chat Resolver: 5 minutes
   - Conversation Manager: 30 seconds

## Next Steps

1. Test the authentication flow
2. Verify multi-tenant isolation
3. Test chat functionality
4. Monitor CloudWatch logs for any issues
5. Set up CloudWatch alarms for production