'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import StakeholderReportView from '../../components/stakeholder-report'
import { Button } from '../../components/ui/button'
import { APIError, clearLocalStorage, getLocalStorage, getStakeholderDecision, setLocalStorage, StorageKeys } from '../../lib/api'
import { StakeholderReport } from '../../lib/types'

export default function StakeholderPage() {
  const router = useRouter()
  const [sessionId, setSessionId] = useState('')
  const [report, setReport] = useState<StakeholderReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    const storedSession = getLocalStorage<string>(StorageKeys.INTERVIEW_SESSION_ID) || ''
    const storedReport = getLocalStorage<StakeholderReport>(StorageKeys.STAKEHOLDER_REPORT)

    if (!storedSession) {
      router.replace('/debrief')
      return
    }

    setSessionId(storedSession)
    if (storedReport && storedReport.session_id === storedSession) {
      setReport(storedReport)
    }
  }, [router])

  const generateReport = async () => {
    if (!sessionId) {
      setErrorMessage('Session is missing. Return to interview and try again.')
      return
    }

    setLoading(true)
    setErrorMessage('')

    try {
      const stakeholderReport = await getStakeholderDecision(sessionId)
      setReport(stakeholderReport)
      setLocalStorage(StorageKeys.STAKEHOLDER_REPORT, stakeholderReport)
    } catch (error) {
      if (error instanceof APIError) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage('Unable to generate stakeholder decision right now.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background py-6">
      {report ? (
        <StakeholderReportView report={report} />
      ) : (
        <main className="mx-auto max-w-4xl border border-ink-primary p-6">
          <p className="section-label">STAGE 03</p>
          <h1 className="display-tight mt-1 text-4xl">GENERATE STAKEHOLDER DECISION</h1>
          <p className="mt-2" style={{ color: 'var(--ink-secondary)' }}>
            Simulate the hiring panel and produce a consensus decision from hiring manager, technical lead, HR, and peer engineering perspectives.
          </p>
          <div className="rule-thin my-4" />
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="section-label">INPUT</p>
              <p className="mono-data text-sm">Interview debrief</p>
            </div>
            <div>
              <p className="section-label">PROCESS</p>
              <p className="mono-data text-sm">Weighted consensus</p>
            </div>
            <div>
              <p className="section-label">OUTPUT</p>
              <p className="mono-data text-sm">Hire / No-hire recommendation</p>
            </div>
          </div>

          {errorMessage ? (
            <p className="mt-4 text-sm" style={{ color: 'var(--concern)' }}>
              {errorMessage}
            </p>
          ) : null}

          <Button className="mt-5 px-5 py-2 text-sm font-bold tracking-[0.08em]" onClick={() => void generateReport()} disabled={loading}>
            {loading ? 'GENERATING...' : 'GENERATE DECISION'}
          </Button>
        </main>
      )}

      <footer className="mx-auto mt-6 flex w-full max-w-6xl items-center justify-between border-t-2 border-ink-primary p-4">
        <Button variant="ghost" className="px-4 py-2 text-sm" onClick={() => router.push('/debrief')}>
          BACK TO DEBRIEF
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
