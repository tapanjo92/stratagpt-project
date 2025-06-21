'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { XMarkIcon } from '@heroicons/react/24/outline'

interface AuthModalProps {
  onClose: () => void
}

export default function AuthModal({ onClose }: AuthModalProps) {
  const { signIn, signUp, confirmSignUp, error, clearError } = useAuth()
  const [mode, setMode] = useState<'signin' | 'signup' | 'confirm'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [tenantId, setTenantId] = useState('')
  const [confirmationCode, setConfirmationCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      await signIn(email, password)
      onClose()
    } catch (err) {
      console.error('Sign in error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      await signUp(email, password, tenantId)
      setMode('confirm')
    } catch (err) {
      console.error('Sign up error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleConfirmSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      await confirmSignUp(email, confirmationCode)
      setMode('signin')
      clearError()
    } catch (err) {
      console.error('Confirmation error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const switchMode = (newMode: typeof mode) => {
    setMode(newMode)
    clearError()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'signin' ? 'Sign In' : mode === 'signup' ? 'Create Account' : 'Confirm Account'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {mode === 'signin' && (
          <form onSubmit={handleSignIn} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-strata-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-strata-500"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-strata-600 text-white py-2 rounded-lg hover:bg-strata-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>

            <p className="text-center text-sm text-gray-600">
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => switchMode('signup')}
                className="text-strata-600 hover:text-strata-700 font-medium"
              >
                Sign up
              </button>
            </p>
          </form>
        )}

        {mode === 'signup' && (
          <form onSubmit={handleSignUp} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-strata-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-strata-500"
                required
                minLength={8}
              />
              <p className="text-xs text-gray-500 mt-1">
                Must be at least 8 characters
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tenant ID
              </label>
              <input
                type="text"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-strata-500"
                placeholder="e.g., strata-plan-12345"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-strata-600 text-white py-2 rounded-lg hover:bg-strata-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Creating account...' : 'Create Account'}
            </button>

            <p className="text-center text-sm text-gray-600">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => switchMode('signin')}
                className="text-strata-600 hover:text-strata-700 font-medium"
              >
                Sign in
              </button>
            </p>
          </form>
        )}

        {mode === 'confirm' && (
          <form onSubmit={handleConfirmSignUp} className="space-y-4">
            <p className="text-gray-600 mb-4">
              We've sent a confirmation code to {email}. Please enter it below.
            </p>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confirmation Code
              </label>
              <input
                type="text"
                value={confirmationCode}
                onChange={(e) => setConfirmationCode(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-strata-500"
                placeholder="123456"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-strata-600 text-white py-2 rounded-lg hover:bg-strata-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Confirming...' : 'Confirm Account'}
            </button>

            <p className="text-center text-sm text-gray-600">
              Didn't receive the code?{' '}
              <button
                type="button"
                onClick={() => console.log('Resend code')}
                className="text-strata-600 hover:text-strata-700 font-medium"
              >
                Resend
              </button>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}