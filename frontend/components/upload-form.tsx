'use client'

import { useCallback, useState } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Toast } from './ui/toast'

interface UploadFormProps {
  onSubmit: (file: File, company: string, role: string) => Promise<void> | void
  disabled?: boolean
}

function formatFileSize(bytes: number): string {
  const kb = bytes / 1024
  if (kb < 1024) {
    return `${Math.round(kb)} KB`
  }

  const mb = kb / 1024
  return `${mb.toFixed(1)} MB`
}

export default function UploadForm({ onSubmit, disabled = false }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null)
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')
  const [isDragOver, setIsDragOver] = useState(false)
  const [toastOpen, setToastOpen] = useState(false)

  const rejectNonPdf = useCallback(() => {
    setToastOpen(true)
  }, [])

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault()
      setIsDragOver(false)

      const droppedFile = event.dataTransfer.files?.[0]
      if (!droppedFile) {
        return
      }

      if (droppedFile.type !== 'application/pdf') {
        rejectNonPdf()
        return
      }

      setFile(droppedFile)
    },
    [rejectNonPdf]
  )

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (!selectedFile) {
      return
    }

    if (selectedFile.type !== 'application/pdf') {
      rejectNonPdf()
      return
    }

    setFile(selectedFile)
  }

  const canSubmit = Boolean(file && company.trim() && role.trim() && !disabled)

  return (
    <div className="space-y-6">
      <Toast
        open={toastOpen}
        title="INVALID FILE TYPE"
        description="Only PDF resumes are accepted."
        onClose={() => setToastOpen(false)}
      />

      <div
        className="cursor-pointer border border-dashed border-ink-primary p-8 transition-colors duration-150"
        style={{
          background: isDragOver ? 'var(--ink-primary)' : 'var(--surface)',
          color: isDragOver ? 'var(--accent-white)' : 'var(--ink-primary)',
        }}
        onClick={() => document.getElementById('resume-upload-input')?.click()}
        onDrop={handleDrop}
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragOver(true)
        }}
        onDragLeave={() => setIsDragOver(false)}
      >
        <input id="resume-upload-input" type="file" accept=".pdf" className="hidden" onChange={handleFileSelect} />

        {file ? (
          <div className="text-center">
            <p className="mono-data text-sm text-positive">[OK] FILE ATTACHED</p>
            <p className="mono-data mt-1 text-base font-bold">{file.name}</p>
            <p className="mono-data text-xs" style={{ color: 'var(--ink-muted)' }}>
              {formatFileSize(file.size)}
            </p>
          </div>
        ) : (
          <div className="text-center">
            <p className="section-label text-sm" style={{ color: isDragOver ? 'var(--accent-white)' : 'var(--ink-primary)' }}>
              DROP RESUME HERE
            </p>
            <p className="ui-label mt-1 text-xs" style={{ color: isDragOver ? 'var(--accent-white)' : 'var(--ink-muted)' }}>
              PDF files only
            </p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Input
          value={company}
          onChange={(event) => setCompany(event.target.value)}
          placeholder="Target Company"
          aria-label="Target Company"
          disabled={disabled}
        />
        <Input
          value={role}
          onChange={(event) => setRole(event.target.value)}
          placeholder="Target Role"
          aria-label="Target Role"
          disabled={disabled}
        />
      </div>

      <Button
        type="button"
        className="w-full px-4 py-3 text-center text-sm font-bold tracking-[0.08em]"
        onClick={() => {
          if (!file) {
            return
          }

          void onSubmit(file, company.trim(), role.trim())
        }}
        disabled={!canSubmit}
      >
        ANALYZE RESUME
      </Button>
    </div>
  )
}
