'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'

declare global {
  interface Window {
    webkitSpeechRecognition?: {
      new (): SpeechRecognition
    }
    SpeechRecognition?: {
      new (): SpeechRecognition
    }
  }
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

interface VoiceInputProps {
  onSubmit: (message: string) => Promise<void>
  onEndInterview: () => Promise<void>
  busy: boolean
}

export default function VoiceInput({ onSubmit, onEndInterview, busy }: VoiceInputProps) {
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const silenceTimerRef = useRef<number | null>(null)

  const [isSupported, setIsSupported] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [statusText, setStatusText] = useState('Press mic to speak')
  const [textFallback, setTextFallback] = useState('')

  const transcriptBufferRef = useRef('')

  useEffect(() => {
    const isLocalhost =
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1' ||
      window.location.hostname === '[::1]'
    const isSecureAllowed = window.isSecureContext || isLocalhost

    if (!isSecureAllowed) {
      setIsSupported(false)
      setStatusText('Voice input requires HTTPS (or localhost). Using text fallback.')
      return
    }

    const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognitionCtor) {
      setIsSupported(false)
      setStatusText('Browser speech recognition unavailable')
      return
    }

    setIsSupported(true)
    const recognition = new SpeechRecognitionCtor()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let latest = ''
      for (let i = event.results.length - 1; i >= 0; i -= 1) {
        const alt = event.results[i][0]
        if (alt?.transcript) {
          latest = alt.transcript
          break
        }
      }

      transcriptBufferRef.current = latest.trim()
      if (transcriptBufferRef.current) {
        setStatusText('Listening...')
      }

      if (silenceTimerRef.current) {
        window.clearTimeout(silenceTimerRef.current)
      }

      silenceTimerRef.current = window.setTimeout(() => {
        recognition.stop()
      }, 1500)
    }

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      setIsListening(false)

      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setIsSupported(false)
        setStatusText('Microphone permission denied. Using text fallback.')
        return
      }

      if (event.error === 'network') {
        setStatusText('Speech service unavailable. Check connection or use text input.')
        return
      }

      setStatusText('Speech capture error, try again')
    }

    recognition.onend = () => {
      setIsListening(false)

      if (silenceTimerRef.current) {
        window.clearTimeout(silenceTimerRef.current)
        silenceTimerRef.current = null
      }

      const message = transcriptBufferRef.current.trim()
      transcriptBufferRef.current = ''

      if (!message || busy) {
        setStatusText(busy ? 'Processing...' : 'Press mic to speak')
        return
      }

      setStatusText('Processing...')
      void onSubmit(message).finally(() => {
        setStatusText('Press mic to speak')
      })
    }

    recognitionRef.current = recognition

    return () => {
      recognition.stop()
      recognitionRef.current = null
      if (silenceTimerRef.current) {
        window.clearTimeout(silenceTimerRef.current)
      }
    }
  }, [busy, onSubmit])

  const startListening = () => {
    if (!recognitionRef.current || busy) {
      return
    }

    transcriptBufferRef.current = ''
    setStatusText('Listening...')
    setIsListening(true)

    try {
      recognitionRef.current.start()
    } catch {
      setIsListening(false)
      setStatusText('Could not start microphone. Using text fallback.')
      setIsSupported(false)
    }
  }

  const submitTypedInput = async () => {
    const trimmed = textFallback.trim()
    if (!trimmed || busy) {
      return
    }

    setStatusText('Processing...')
    setTextFallback('')
    await onSubmit(trimmed)
    setStatusText('Press mic to speak')
  }

  return (
    <div className="flex items-center gap-3 border-t border-ink-primary p-3">
      {isSupported ? (
        <button
          type="button"
          onClick={startListening}
          disabled={busy}
          className={`h-10 w-10 border border-ink-primary text-base ${isListening ? 'listening-pulse bg-ink-primary text-accent-white' : ''}`}
          aria-label="Start voice input"
        >
          ●
        </button>
      ) : (
        <p className="mono-data text-xs italic" style={{ color: 'var(--ink-muted)' }}>
          MIC OFF
        </p>
      )}

      <Input
        value={textFallback}
        onChange={(event) => setTextFallback(event.target.value)}
        placeholder="Type your answer"
        disabled={busy}
        className="flex-1"
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            void submitTypedInput()
          }
        }}
      />

      <Button variant="ghost" className="px-3 py-2 text-xs" onClick={() => void submitTypedInput()} disabled={busy || !textFallback.trim()}>
        SEND
      </Button>

      <p className="mono-data min-w-[12rem] text-xs italic" style={{ color: 'var(--ink-muted)' }}>
        {busy ? 'Processing...' : statusText}
      </p>

      <Button variant="ghost" className="px-3 py-2 text-xs" onClick={() => void onEndInterview()} disabled={busy}>
        END INTERVIEW
      </Button>
    </div>
  )
}
