'use client'

import { useState, useRef, useEffect } from 'react'
import { PaperAirplaneIcon, DocumentIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/AuthContext'
import MessageList from './MessageList'
import FileUpload from './FileUpload'
import { ChatMessage, Conversation } from '@/types/chat'
import { chatApi } from '@/lib/api'

export default function ChatInterface() {
  const { user } = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showFileUpload, setShowFileUpload] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (user) {
      createNewConversation()
    }
  }, [user])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const createNewConversation = async () => {
    try {
      const conversation = await chatApi.createConversation(user!.tenantId)
      setCurrentConversation(conversation)
      setConversations([conversation, ...conversations])
      setMessages([])
    } catch (error) {
      console.error('Failed to create conversation:', error)
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || !currentConversation || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    }

    setMessages([...messages, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await chatApi.sendMessage(
        user!.tenantId,
        currentConversation.id,
        input
      )

      const assistantMessage: ChatMessage = {
        id: response.message_id,
        role: 'assistant',
        content: response.content,
        timestamp: new Date().toISOString(),
        citations: response.citations
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Failed to send message:', error)
      // Add error message
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleFileUpload = async (file: File) => {
    // This will be implemented to upload to S3
    console.log('File upload:', file)
    setShowFileUpload(false)
    // Show success message
  }

  return (
    <div className="flex h-[calc(100vh-200px)] bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Sidebar with conversations */}
      <div className="w-64 bg-gray-50 border-r border-gray-200 p-4">
        <button
          onClick={createNewConversation}
          className="w-full bg-strata-600 text-white px-4 py-2 rounded-lg hover:bg-strata-700 transition-colors mb-4"
        >
          New Conversation
        </button>
        
        <div className="space-y-2">
          {conversations.map(conv => (
            <button
              key={conv.id}
              onClick={() => setCurrentConversation(conv)}
              className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                currentConversation?.id === conv.id
                  ? 'bg-strata-100 text-strata-900'
                  : 'hover:bg-gray-100'
              }`}
            >
              <div className="font-medium truncate">{conv.title}</div>
              <div className="text-xs text-gray-500">
                {new Date(conv.created_at).toLocaleDateString()}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">
              <p className="text-lg mb-2">Welcome to Australian Strata GPT!</p>
              <p>Ask me anything about strata management, by-laws, or regulations.</p>
            </div>
          ) : (
            <MessageList messages={messages} />
          )}
          
          {isLoading && (
            <div className="flex items-center space-x-2 text-gray-500 mt-4">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
              <span className="text-sm">Assistant is thinking...</span>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex items-end space-x-2">
            <button
              onClick={() => setShowFileUpload(!showFileUpload)}
              className="p-2 text-gray-500 hover:text-gray-700 transition-colors"
              title="Upload document"
            >
              <DocumentIcon className="w-6 h-6" />
            </button>
            
            <div className="flex-1">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question about strata management..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-strata-500 resize-none"
                rows={1}
                disabled={isLoading || !currentConversation}
              />
            </div>
            
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim() || !currentConversation}
              className="p-2 bg-strata-600 text-white rounded-lg hover:bg-strata-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <PaperAirplaneIcon className="w-6 h-6" />
            </button>
          </div>
        </div>
      </div>

      {/* File upload modal */}
      {showFileUpload && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Upload Document</h3>
              <button
                onClick={() => setShowFileUpload(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <XMarkIcon className="w-6 h-6" />
              </button>
            </div>
            <FileUpload onUpload={handleFileUpload} />
          </div>
        </div>
      )}
    </div>
  )
}