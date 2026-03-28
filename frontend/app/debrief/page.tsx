'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import DebriefReportView from '../../components/debrief-report'
import { Button } from '../../components/ui/button'
import { clearLocalStorage, getLocalStorage, StorageKeys } from '../../lib/api'
import { CandidateAnalysis, DebriefReport } from '../../lib/types'

export default function DebriefPage() {
  const router = useRouter()
  const [report, setReport] = useState<DebriefReport | null>(null)
  const [input, setInput] = useState<CandidateAnalysis | null>(null)

  useEffect(() => {
    const storedReport = getLocalStorage<DebriefReport>(StorageKeys.DEBRIEF_REPORT)
    const interviewInput = getLocalStorage<CandidateAnalysis>(StorageKeys.INTERVIEW_INPUT)

    if (!storedReport || !interviewInput) {
      router.replace('/')
      return
    }

    setReport(storedReport)
    setInput(interviewInput)
  }, [router])

  if (!report || !input) {
    return <div className="min-h-screen bg-background" />
  }

  return (
    <div className="min-h-screen bg-background">
      <main className="print-only-content py-6">
        <DebriefReportView
          report={report}
          candidateName={input.candidate_profile?.name || 'Candidate'}
          targetRole={input.target_role || 'Role unavailable'}
          targetCompany={input.target_company || 'Company unavailable'}
        />
      </main>

      <footer className="no-print mx-auto flex w-full max-w-5xl items-center justify-between border-t-2 border-ink-primary p-4">
        <Button variant="ghost" className="px-4 py-2 text-sm" onClick={() => window.print()}>
          DOWNLOAD REPORT
        </Button>
        <Button variant="ghost" className="px-4 py-2 text-sm" onClick={() => router.push('/stakeholder')}>
          STAKEHOLDER DECISION →
        </Button>
        <Button
          className="px-4 py-2 text-sm font-bold tracking-[0.08em]"
          onClick={() => {
            clearLocalStorage()
            router.push('/')
          }}
        >
          NEW ANALYSIS →
        </Button>
      </footer>
    </div>
  )
}
