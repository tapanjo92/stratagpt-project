'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { Amplify } from 'aws-amplify'
import { signIn, signUp, signOut, getCurrentUser, confirmSignUp, resendSignUpCode, fetchAuthSession } from 'aws-amplify/auth'

// Configure Amplify
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_USER_POOL_ID!,
      userPoolClientId: process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID!,
    }
  }
})

interface User {
  username: string
  email: string
  tenantId: string
  role: 'owner' | 'manager' | 'admin'
  attributes?: Record<string, string>
}

interface AuthContextType {
  user: User | null
  loading: boolean
  error: string | null
  signIn: (username: string, password: string) => Promise<void>
  signUp: (email: string, password: string, tenantId: string) => Promise<void>
  confirmSignUp: (username: string, code: string) => Promise<void>
  resendConfirmationCode: (username: string) => Promise<void>
  signOut: () => Promise<void>
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    checkUser()
  }, [])

  const checkUser = async () => {
    try {
      const currentUser = await getCurrentUser()
      if (currentUser) {
        // Fetch the actual user attributes from the auth session
        const session = await fetchAuthSession()
        const idToken = session.tokens?.idToken
        
        if (idToken) {
          // Extract custom attributes from the ID token
          const tenantId = idToken['custom:tenant_id'] || 'default'
          const role = idToken['custom:role'] || 'owner'
          const email = idToken['email'] || currentUser.username
          
          setUser({
            username: currentUser.username,
            email: email,
            tenantId: tenantId,
            role: role as 'owner' | 'manager' | 'admin'
          })
        } else {
          // Fallback if no ID token
          setUser({
            username: currentUser.username,
            email: currentUser.username,
            tenantId: 'default',
            role: 'owner'
          })
        }
      }
    } catch (err) {
      console.log('Not authenticated:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSignIn = async (username: string, password: string) => {
    try {
      setError(null)
      setLoading(true)
      
      const { isSignedIn } = await signIn({ username, password })
      
      if (isSignedIn) {
        await checkUser()
      }
    } catch (err: any) {
      setError(err.message || 'Failed to sign in')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const handleSignUp = async (email: string, password: string, tenantId: string) => {
    try {
      setError(null)
      setLoading(true)
      
      await signUp({
        username: email,
        password,
        options: {
          userAttributes: {
            email,
            'custom:tenant_id': tenantId,
            'custom:role': 'owner'
          }
        }
      })
    } catch (err: any) {
      setError(err.message || 'Failed to sign up')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmSignUp = async (username: string, code: string) => {
    try {
      setError(null)
      setLoading(true)
      
      await confirmSignUp({ username, confirmationCode: code })
    } catch (err: any) {
      setError(err.message || 'Failed to confirm sign up')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const handleResendCode = async (username: string) => {
    try {
      setError(null)
      await resendSignUpCode({ username })
    } catch (err: any) {
      setError(err.message || 'Failed to resend code')
      throw err
    }
  }

  const handleSignOut = async () => {
    try {
      setError(null)
      setLoading(true)
      
      await signOut()
      setUser(null)
    } catch (err: any) {
      setError(err.message || 'Failed to sign out')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const clearError = () => setError(null)

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        signIn: handleSignIn,
        signUp: handleSignUp,
        confirmSignUp: handleConfirmSignUp,
        resendConfirmationCode: handleResendCode,
        signOut: handleSignOut,
        clearError
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}