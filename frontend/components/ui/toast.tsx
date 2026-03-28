'use client'

import { useEffect } from 'react'

interface ToastProps {
  open: boolean
  title: string
  description?: string
  onClose: () => void
}

export function Toast({ open, title, description, onClose }: ToastProps) {
  useEffect(() => {
    if (!open) {
      return
    }

    const id = window.setTimeout(() => onClose(), 3200)
    return () => window.clearTimeout(id)
  }, [open, onClose])

  if (!open) {
    return null
  }

  return (
    <div className="fixed right-4 top-4 z-50 w-full max-w-sm border border-ink-primary bg-background p-3">
      <p className="font-mono text-xs font-bold tracking-[0.12em]">{title}</p>
      {description ? <p className="mt-1 text-sm text-ink-secondary">{description}</p> : null}
      <button className="mt-2 text-xs ui-label underline" onClick={onClose} type="button">
        DISMISS
      </button>
    </div>
  )
}
