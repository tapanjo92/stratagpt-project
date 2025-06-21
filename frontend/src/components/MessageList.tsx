'use client'

import ReactMarkdown from 'react-markdown'
import { ChatMessage } from '@/types/chat'
import { UserCircleIcon } from '@heroicons/react/24/solid'
import { format } from 'date-fns'

interface MessageListProps {
  messages: ChatMessage[]
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex items-start space-x-3 message-animation ${
            message.role === 'user' ? 'justify-end' : ''
          }`}
        >
          {message.role === 'assistant' && (
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-strata-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-semibold">AI</span>
              </div>
            </div>
          )}
          
          <div
            className={`max-w-2xl px-4 py-2 rounded-lg ${
              message.role === 'user'
                ? 'bg-strata-600 text-white'
                : message.isError
                ? 'bg-red-50 text-red-900 border border-red-200'
                : 'bg-gray-100 text-gray-900'
            }`}
          >
            <div className="prose prose-sm max-w-none">
              {message.role === 'user' ? (
                <p className="text-white whitespace-pre-wrap">{message.content}</p>
              ) : (
                <ReactMarkdown
                  className={message.role === 'user' ? 'text-white' : ''}
                  components={{
                    p: ({ children }) => <p className="mb-2">{children}</p>,
                    ul: ({ children }) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
                    li: ({ children }) => <li className="mb-1">{children}</li>,
                    code: ({ inline, children }) =>
                      inline ? (
                        <code className="bg-gray-200 px-1 rounded">{children}</code>
                      ) : (
                        <pre className="bg-gray-800 text-white p-2 rounded overflow-x-auto">
                          <code>{children}</code>
                        </pre>
                      ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              )}
            </div>
            
            {message.citations && message.citations.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-200">
                <p className="text-xs text-gray-600">
                  Citations: {message.citations.length} source(s)
                </p>
              </div>
            )}
            
            <div className="text-xs text-gray-500 mt-1">
              {format(new Date(message.timestamp), 'HH:mm')}
            </div>
          </div>
          
          {message.role === 'user' && (
            <div className="flex-shrink-0">
              <UserCircleIcon className="w-8 h-8 text-gray-400" />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}