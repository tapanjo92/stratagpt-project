'use client'

import { useState, useCallback } from 'react'
import { DocumentArrowUpIcon } from '@heroicons/react/24/outline'

interface FileUploadProps {
  onUpload: (file: File) => void
  accept?: string
  maxSize?: number // in MB
}

export default function FileUpload({ 
  onUpload, 
  accept = '.pdf,.docx,.txt',
  maxSize = 10 
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      handleFile(files[0])
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFile(files[0])
    }
  }

  const handleFile = (file: File) => {
    setError(null)
    
    // Validate file size
    const maxSizeBytes = maxSize * 1024 * 1024
    if (file.size > maxSizeBytes) {
      setError(`File size must be less than ${maxSize}MB`)
      return
    }
    
    // Validate file type
    const fileExtension = `.${file.name.split('.').pop()?.toLowerCase()}`
    const acceptedExtensions = accept.split(',')
    
    if (!acceptedExtensions.includes(fileExtension)) {
      setError('Invalid file type. Please upload PDF, DOCX, or TXT files.')
      return
    }
    
    onUpload(file)
  }

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-strata-600 bg-strata-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input
          type="file"
          accept={accept}
          onChange={handleFileSelect}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        
        <DocumentArrowUpIcon className="w-12 h-12 mx-auto text-gray-400 mb-4" />
        
        <p className="text-gray-600 mb-2">
          Drag and drop your document here, or click to select
        </p>
        
        <p className="text-sm text-gray-500">
          Supported formats: PDF, DOCX, TXT (max {maxSize}MB)
        </p>
      </div>
      
      {error && (
        <p className="mt-2 text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}