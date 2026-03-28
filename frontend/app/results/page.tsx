'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import CandidateDossier from '@/components/candidate-dossier'
import GitHubSignals from '@/components/github-signals'
import InterviewThreads from '@/components/interview-threads'
import ScoreCard from '@/components/score-card'
import SignalColumns from '@/components/signal-columns'
import { getLocalStorage, setLocalStorage, StorageKeys } from '@/lib/api'
import { CandidateAnalysis } from '@/lib/types'

function formatDate(dateString: string): string {
  if (!dateString) {
    return 'Unknown date'
  }

  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function ResultsPage() {
  const router = useRouter()
  const [analysis, setAnalysis] = useState<CandidateAnalysis | null>(null)

  useEffect(() => {
    const data = getLocalStorage<CandidateAnalysis>(StorageKeys.CANDIDATE_ANALYSIS)
    if (!data) {
      router.replace('/')
      return
    }

    setAnalysis(data)
  }, [router])

  const score = useMemo(() => Math.max(0, Math.min(50, Math.round(analysis?.score_breakdown?.overall_score || 0))), [analysis])

  if (!analysis) {
    return <div className="min-h-screen bg-background" />
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-20 border-b border-ink-primary bg-ink-primary px-6 py-3 text-accent-white">
        <div className="mx-auto flex w-full max-w-[1600px] items-center justify-between gap-4">
          <p className="text-lg font-bold leading-tight">
            {analysis.candidate_profile?.name || 'Candidate'} — {analysis.target_role || 'Role'} at {analysis.target_company || 'Company'}
          </p>
          <div className="flex items-center gap-3">
            <p className="mono-data text-xs">{formatDate(analysis.analysis_date)}</p>
            <span
              className="mono-data px-3 py-1 text-sm"
              style={{
                border: '1px solid var(--accent-white)',
                borderRadius: '2px',
              }}
            >
              {score}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto grid min-h-[calc(100vh-128px)] w-full max-w-[1600px] grid-cols-3">
        <section className="border-r border-border-light p-6">
          <CandidateDossier profile={analysis.candidate_profile} targetRole={analysis.target_role} />
        </section>

        <section className="border-r border-border-light p-6">
          <ScoreCard scoreBreakdown={analysis.score_breakdown} />
          <div className="rule-thin my-5" />
          <GitHubSignals signals={analysis.github_signals} />
        </section>

        <section className="p-6">
          <SignalColumns strongSignals={analysis.strong_signals || []} weakSignals={analysis.weak_signals || []} />
          <div className="rule-thin my-5" />
          <InterviewThreads threads={analysis.interview_threads || []} />
        </section>
      </main>

      <footer className="sticky bottom-0 z-20 border-t border-ink-primary bg-ink-primary px-6 py-3 text-accent-white">
        <div className="mx-auto flex w-full max-w-[1600px] items-center justify-between gap-4">
          <div>
            <p className="section-label" style={{ color: 'var(--ink-muted)' }}>
              READY TO INTERVIEW?
            </p>
            <p className="text-lg font-bold">
              {analysis.candidate_profile?.name || 'Candidate'} · {analysis.target_role || 'Role'} at {analysis.target_company || 'Company'}
            </p>
          </div>
          <button
            className="btn-core bg-transparent px-4 py-2 text-sm font-bold tracking-[0.08em]"
            style={{ color: 'var(--accent-white)', borderColor: 'var(--accent-white)' }}
            onClick={() => {
              setLocalStorage(StorageKeys.INTERVIEW_INPUT, analysis)
              router.push('/interview')
            }}
            type="button"
          >
            BEGIN INTERVIEW →
          </button>
        </div>
      </footer>
    </div>
  )
}
