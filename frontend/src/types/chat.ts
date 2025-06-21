export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  citations?: Citation[]
  isError?: boolean
}

export interface Citation {
  document_id: string
  title: string
  excerpt: string
  confidence?: number
}

export interface Conversation {
  id: string
  title: string
  status: 'active' | 'archived'
  created_at: string
  updated_at: string
  message_count: number
}

export interface SendMessageResponse {
  conversation_id: string
  message_id: string
  content: string
  citations: Citation[]
  generation_time_ms: number
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}