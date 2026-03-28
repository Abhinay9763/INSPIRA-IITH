'use client'

import { useEffect, useRef } from 'react'
import { InterviewTurn } from '../lib/types'

interface InterviewTranscriptProps {
  turns: InterviewTurn[]
}

export default function InterviewTranscript({ turns }: InterviewTranscriptProps) {
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns])

  return (
    <section className="space-y-3">
      {turns.map((turn, index) => {
        const isInterviewer = turn.speaker === 'interviewer'
        return (
          <article key={`${turn.timestamp}-${index}`} className="border-b border-muted-rule pb-3">
            <p className="mono-data text-xs font-bold tracking-[0.12em]">{isInterviewer ? 'ALEX' : 'YOU'}</p>
            <p className="mt-1 pl-6">{turn.text}</p>
            <p className="mono-data mt-1 pl-6 text-[11px]" style={{ color: 'var(--ink-muted)' }}>
              {new Date(turn.timestamp).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}
            </p>
          </article>
        )
      })}
      <div ref={endRef} />
    </section>
  )
}
