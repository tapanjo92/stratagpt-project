'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import ChatInterface from '@/components/ChatInterface'
import AuthModal from '@/components/AuthModal'
import Header from '@/components/Header'

export default function Home() {
  const { user, loading } = useAuth()
  const [showAuthModal, setShowAuthModal] = useState(false)

  useEffect(() => {
    if (!loading && !user) {
      setShowAuthModal(true)
    }
  }, [loading, user])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-strata-600"></div>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <Header />
      
      {user ? (
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-6xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900 mb-8">
              Australian Strata GPT Assistant
            </h1>
            <ChatInterface />
          </div>
        </div>
      ) : (
        <div className="container mx-auto px-4 py-16">
          <div className="max-w-2xl mx-auto text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Welcome to Australian Strata GPT
            </h1>
            <p className="text-xl text-gray-600 mb-8">
              Your AI-powered assistant for strata management questions
            </p>
            <button
              onClick={() => setShowAuthModal(true)}
              className="bg-strata-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-strata-700 transition-colors"
            >
              Sign In to Continue
            </button>
          </div>
        </div>
      )}

      {showAuthModal && !user && (
        <AuthModal onClose={() => setShowAuthModal(false)} />
      )}
    </main>
  )
}