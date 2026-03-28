'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { transcribeWithWhisperWasm } from '../lib/whisper-wasm'

interface VoiceInputProps {
  onSubmit: (message: string) => Promise<void>
  onEndInterview: () => Promise<void>
  busy: boolean
}

export default function VoiceInput({ onSubmit, onEndInterview, busy }: VoiceInputProps) {
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  const [isSupported, setIsSupported] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [statusText, setStatusText] = useState('Press REC to record')
  const [textFallback, setTextFallback] = useState('')

  useEffect(() => {
    const isLocalhost =
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1' ||
      window.location.hostname === '[::1]'
    const isSecureAllowed = window.isSecureContext || isLocalhost

    if (!isSecureAllowed) {
      setIsSupported(false)
      setStatusText('Mic recording requires HTTPS (or localhost). Use text fallback.')
      return
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof window.MediaRecorder === 'undefined') {
      setIsSupported(false)
      setStatusText('Media recorder unavailable in this browser')
      return
    }

    setIsSupported(true)

    return () => {
      if (recorderRef.current && recorderRef.current.state !== 'inactive') {
        recorderRef.current.stop()
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
        streamRef.current = null
      }
    }
  }, [])

  const detectMimeType = (): string | undefined => {
    const options = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
    for (const mimeType of options) {
      if (MediaRecorder.isTypeSupported(mimeType)) {
        return mimeType
      }
    }
    return undefined
  }

  const startRecording = async () => {
    if (!isSupported || busy || isTranscribing || isRecording) {
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const mimeType = detectMimeType()
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)

      audioChunksRef.current = []

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        audioChunksRef.current = []

        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop())
          streamRef.current = null
        }

        if (!blob.size || busy) {
          setStatusText('Press REC to record')
          return
        }

        setIsTranscribing(true)
        void transcribeWithWhisperWasm(blob, (next) => setStatusText(next))
          .then(async (text) => {
            if (!text.trim()) {
              throw new Error('Could not transcribe speech')
            }
            setStatusText('Sending response...')
            await onSubmit(text)
            setStatusText('Press REC to record')
          })
          .catch((error: unknown) => {
            const message = error instanceof Error ? error.message : 'Transcription failed'
            setStatusText(message)
          })
          .finally(() => {
            setIsTranscribing(false)
          })
      }

      recorderRef.current = recorder
      recorder.start()
      setIsRecording(true)
      setStatusText('Recording... press STOP')
    } catch {
      setIsRecording(false)
      setStatusText('Could not access microphone. Use text input.')
      setIsSupported(false)
    }
  }

  const stopRecording = () => {
    if (!recorderRef.current || recorderRef.current.state === 'inactive') {
      return
    }
    recorderRef.current.stop()
    setIsRecording(false)
    setStatusText('Preparing audio...')
  }

  const submitTypedInput = async () => {
    const trimmed = textFallback.trim()
    if (!trimmed || busy) {
      return
    }

    setStatusText('Processing...')
    setTextFallback('')
    await onSubmit(trimmed)
    setStatusText('Press REC to record')
  }

  return (
    <div className="flex items-center gap-3 border-t border-ink-primary p-3">
      {isSupported ? (
        <button
          type="button"
          onClick={isRecording ? stopRecording : () => void startRecording()}
          disabled={busy || isTranscribing}
          className={`h-10 w-14 border border-ink-primary text-xs ${isRecording ? 'listening-pulse bg-ink-primary text-accent-white' : ''}`}
          aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        >
          {isRecording ? 'STOP' : 'REC'}
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
        disabled={busy || isTranscribing}
        className="flex-1"
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            void submitTypedInput()
          }
        }}
      />

      <Button variant="ghost" className="px-3 py-2 text-xs" onClick={() => void submitTypedInput()} disabled={busy || isTranscribing || !textFallback.trim()}>
        SEND
      </Button>

      <p className="mono-data min-w-[12rem] text-xs italic" style={{ color: 'var(--ink-muted)' }}>
        {busy || isTranscribing ? statusText : statusText}
      </p>

      <Button variant="ghost" className="px-3 py-2 text-xs" onClick={() => void onEndInterview()} disabled={busy || isTranscribing}>
        END INTERVIEW
      </Button>
    </div>
  )
}
