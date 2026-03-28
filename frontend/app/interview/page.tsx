'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import InterviewTranscript from '../../components/interview-transcript'
import VoiceInput from '../../components/voice-input'
import { Toast } from '../../components/ui/toast'
import {
  APIError,
  appendInterviewTurn,
  endInterview,
  getLocalStorage,
  sendInterviewTurn,
  setLocalStorage,
  startInterview,
  StorageKeys,
} from '../../lib/api'
import { CandidateAnalysis, InterviewTurn } from '../../lib/types'

const PHASES = ['WARMUP', 'DEEP DIVE', 'TECHNICAL', 'CLOSING']

function nowIso(): string {
  return new Date().toISOString()
}

function toMmSs(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function normalizeCandidateIntro(message: string, candidateName?: string): string {
  const text = message.trim()
  if (!text) {
    return text
  }

  const name = (candidateName || '').trim()
  if (!name) {
    return text
  }

  // Cheeky demo hack: replace speech-recognition "I am / I'm" opener with candidate name.
  return text.replace(/^(i\s*am|i['’]?m)\s+/i, `${name} `)
}

async function playBase64Audio(audioBase64: string): Promise<void> {
  if (!audioBase64) {
    return
  }

  const src = audioBase64.startsWith('data:audio') ? audioBase64 : `data:audio/mpeg;base64,${audioBase64}`

  try {
    const audio = new Audio(src)
    await audio.play()
  } catch {
    // Ignore autoplay restrictions and keep transcript state moving.
  }
}

export default function InterviewPage() {
  const router = useRouter()
  const [analysis, setAnalysis] = useState<CandidateAnalysis | null>(null)
  const [sessionId, setSessionId] = useState<string>('')
  const [turns, setTurns] = useState<InterviewTurn[]>([])
  const [busy, setBusy] = useState(false)
  const [currentPhase, setCurrentPhase] = useState(1)
  const [elapsed, setElapsed] = useState(0)
  const [errorMessage, setErrorMessage] = useState('')

  const mountedRef = useRef(false)

  useEffect(() => {
    const interviewInput = getLocalStorage<CandidateAnalysis>(StorageKeys.INTERVIEW_INPUT)
    if (!interviewInput) {
      router.replace('/')
      return
    }

    setAnalysis(interviewInput)
    setSessionId('')
    setTurns([])
    setLocalStorage(StorageKeys.INTERVIEW_HISTORY, [])
    setLocalStorage(StorageKeys.INTERVIEW_SESSION_ID, '')
  }, [router])

  useEffect(() => {
    if (!analysis || mountedRef.current) {
      return
    }

    mountedRef.current = true

    const start = async () => {
      setBusy(true)
      try {
        const response = await startInterview(analysis)
        if (!response.session_id) {
          throw new APIError('Interview session was not initialized. Please restart.', 500)
        }

        setSessionId(response.session_id)
        setLocalStorage(StorageKeys.INTERVIEW_SESSION_ID, response.session_id)

        const firstTurn: InterviewTurn = {
          speaker: 'interviewer',
          text: response.text,
          timestamp: nowIso(),
        }
        setTurns([firstTurn])
        appendInterviewTurn(firstTurn)
        await playBase64Audio(response.audio)
      } catch (error) {
        if (error instanceof APIError) {
          setErrorMessage(error.message)
        } else {
          setErrorMessage('Failed to initialize interview session.')
        }
      } finally {
        setBusy(false)
      }
    }

    void start()
  }, [analysis])

  useEffect(() => {
    const id = window.setInterval(() => setElapsed((prev) => prev + 1), 1000)
    return () => window.clearInterval(id)
  }, [])

  const submitTurn = async (message: string) => {
    if (!message.trim()) {
      return
    }

    if (!sessionId) {
      setErrorMessage('Session is not ready yet. Please wait a moment and try again.')
      return
    }

    setBusy(true)

    const normalizedMessage = normalizeCandidateIntro(message, analysis?.candidate_profile?.name)

    const candidateTurn: InterviewTurn = {
      speaker: 'candidate',
      text: normalizedMessage,
      timestamp: nowIso(),
    }

    setTurns((prev) => [...prev, candidateTurn])
    appendInterviewTurn(candidateTurn)

    try {
      const response = await sendInterviewTurn(normalizedMessage, sessionId)
      setCurrentPhase(Math.max(1, Math.min(4, response.current_phase || 1)))

      const interviewerTurn: InterviewTurn = {
        speaker: 'interviewer',
        text: response.text,
        timestamp: nowIso(),
      }

      setTurns((prev) => [...prev, interviewerTurn])
      appendInterviewTurn(interviewerTurn)
      await playBase64Audio(response.audio)
    } catch (error) {
      if (error instanceof APIError) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage('Unable to send interview turn right now.')
      }
    } finally {
      setBusy(false)
    }
  }

  const finishInterview = async () => {
    if (!sessionId) {
      setErrorMessage('Session is missing. Restart interview from results page.')
      return
    }

    setBusy(true)
    try {
      const report = await endInterview(sessionId)
      setLocalStorage(StorageKeys.DEBRIEF_REPORT, report)
      setLocalStorage(StorageKeys.INTERVIEW_HISTORY, turns)
      router.push('/debrief')
    } catch (error) {
      if (error instanceof APIError) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage('Unable to end interview session.')
      }
      setBusy(false)
    }
  }

  const phaseIndex = useMemo(() => Math.max(1, Math.min(4, currentPhase || 1)), [currentPhase])

  if (!analysis) {
    return <div className="min-h-screen bg-background" />
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Toast
        open={Boolean(errorMessage)}
        title="INTERVIEW ERROR"
        description={errorMessage}
        onClose={() => setErrorMessage('')}
      />

      <aside
        className="flex h-screen w-[30%] flex-col justify-between border-r px-6 py-5 text-accent-white"
        style={{ background: 'var(--ink-primary)', borderColor: 'var(--border-light)' }}
      >
        <div>
          <p className="section-label" style={{ color: 'var(--ink-muted)' }}>
            MOCK INTERVIEW
          </p>
          <h1 className="display-tight mt-2 text-4xl" style={{ color: 'var(--accent-white)' }}>
            {analysis.candidate_profile?.name || 'Candidate'}
          </h1>
          <p className="mt-1 text-lg italic" style={{ color: 'var(--ink-muted)' }}>
            {analysis.target_role || 'Role unavailable'}
          </p>
          <div className="rule-light my-4" />

          <p className="section-label" style={{ color: 'var(--ink-muted)' }}>
            SESSION PROGRESS
          </p>
          <div className="mt-3 space-y-2 border-l border-border-light pl-4">
            {PHASES.map((phase, index) => {
              const row = index + 1
              const done = row < phaseIndex
              const active = row === phaseIndex
              return (
                <div key={phase} className="relative pl-3">
                  <span
                    className="absolute -left-[18px] top-[9px] h-[6px] w-[6px] border"
                    style={{
                      borderColor: done || active ? 'var(--accent-white)' : 'var(--ink-muted)',
                      background: active ? 'var(--accent-white)' : 'transparent',
                    }}
                  />
                  <p
                    className="text-base"
                    style={{
                      color: active ? 'var(--accent-white)' : 'var(--ink-muted)',
                      fontWeight: active ? 700 : 400,
                      textDecoration: done ? 'line-through' : 'none',
                    }}
                  >
                    {phase}
                  </p>
                </div>
              )
            })}
          </div>
        </div>

        <div>
          <div className="rule-light mb-3" />
          <p className="section-label" style={{ color: 'var(--ink-muted)' }}>
            YOUR INTERVIEWER
          </p>
          <p className="mono-data mt-1 text-4xl font-bold">ALEX</p>
          <p className="italic" style={{ color: 'var(--ink-muted)' }}>
            Senior Engineer
          </p>
          <p className="ui-label text-sm" style={{ color: 'var(--ink-muted)' }}>
            {analysis.target_company || 'Target company unavailable'}
          </p>
          <p className="mono-data mt-2 text-lg">{toMmSs(elapsed)}</p>
        </div>
      </aside>

      <section className="flex h-screen w-[70%] flex-col">
        <div className="border-b border-muted-rule px-6 py-4">
          <p className="section-label">INTERVIEW TRANSCRIPT</p>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          <InterviewTranscript turns={turns} />
        </div>

        <VoiceInput onSubmit={submitTurn} onEndInterview={finishInterview} busy={busy} />
      </section>
    </div>
  )
}
