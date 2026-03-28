'use client'

import { useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import ProgressSteps from '@/components/progress-steps'
import UploadForm from '@/components/upload-form'
import { Toast } from '@/components/ui/toast'
import { analyzeResume, APIError, setLocalStorage, StorageKeys } from '@/lib/api'

export default function HomePage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [errorMessage, setErrorMessage] = useState('')

  const timersRef = useRef<number[]>([])

  const clearTimers = () => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer))
    timersRef.current = []
  }

  const scheduleLoadingSteps = () => {
    setCurrentStep(1)
    timersRef.current.push(window.setTimeout(() => setCurrentStep(2), 1500))
    timersRef.current.push(window.setTimeout(() => setCurrentStep(3), 3500))
    timersRef.current.push(window.setTimeout(() => setCurrentStep(4), 5000))
  }

  const handleAnalysis = async (file: File, company: string, role: string) => {
    clearTimers()
    setErrorMessage('')
    setIsLoading(true)
    scheduleLoadingSteps()

    try {
      const analysis = await analyzeResume(file, company, role)
      setCurrentStep(4)
      setLocalStorage(StorageKeys.CANDIDATE_ANALYSIS, analysis)
      router.push('/results')
    } catch (error) {
      clearTimers()
      setCurrentStep(0)
      setIsLoading(false)
      if (error instanceof APIError) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage('Unable to analyze profile right now.')
      }
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Toast
        open={Boolean(errorMessage)}
        title="ANALYSIS FAILED"
        description={errorMessage}
        onClose={() => setErrorMessage('')}
      />

      <header className="border-b border-ink-primary bg-ink-primary px-6 py-3 text-accent-white">
        <div className="mx-auto flex w-full max-w-[1400px] items-center justify-between">
          <p className="text-4xl italic leading-none">INSPIRA</p>
          <p className="ui-label text-xs">Beyond the resume. Beyond the interview.</p>
        </div>
      </header>

      <main className="mx-auto grid min-h-[calc(100vh-58px)] w-full max-w-[1400px] grid-cols-5">
        <section className="col-span-3 border-r border-border-light p-6">
          <h1 className="display-tight text-6xl">Discover talent the resume never reveals.</h1>
          <p className="mt-3 text-xl" style={{ color: 'var(--ink-secondary)' }}>
            INSPIRA reads resumes like editors read manuscripts: line by line, signal by signal. It pairs GitHub forensics with
            adaptive interview design to expose depth, originality, and communication under pressure.
          </p>
          <div className="rule-thin my-5" />

          {isLoading ? <ProgressSteps currentStep={currentStep} /> : <UploadForm onSubmit={handleAnalysis} />}

          <div className="rule-thin my-5" />
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="section-label">INPUTS</p>
              <p className="mono-data">Resume PDF</p>
              <p className="mono-data">Target Company</p>
              <p className="mono-data">Target Role</p>
            </div>
            <div>
              <p className="section-label">OUTPUTS</p>
              <p className="mono-data">Candidate Analysis</p>
              <p className="mono-data">Interview Threads</p>
              <p className="mono-data">Debrief Blueprint</p>
            </div>
            <div>
              <p className="section-label">SCORE MODEL</p>
              <p className="mono-data">5 dimensions</p>
              <p className="mono-data">50-point readiness index</p>
              <p className="mono-data">Evidence-linked rationale</p>
            </div>
          </div>
        </section>

        <aside className="col-span-2 p-6">
          {[
            {
              label: '01 / SIGNAL DISCOVERY',
              title: 'Code footprint over claims',
              text: 'Repository originality, README clarity, and activity history reveal how candidates actually build.',
            },
            {
              label: '02 / INTERVIEW DESIGN',
              title: 'Adaptive, thread-based questioning',
              text: 'Prompts shift from warmup to technical depth according to demonstrated strengths and gaps.',
            },
            {
              label: '03 / DECISION SUPPORT',
              title: 'Debrief built for hiring committees',
              text: 'Output reads like an editorial report: explicit verdicts, traceable scores, and study guidance.',
            },
          ].map((feature) => (
            <article key={feature.label} className="pb-4">
              <p className="section-label">{feature.label}</p>
              <h2 className="display-tight mt-1 text-3xl">{feature.title}</h2>
              <p className="mt-2" style={{ color: 'var(--ink-secondary)' }}>
                {feature.text}
              </p>
              <div className="rule-thin mt-4" />
            </article>
          ))}

          <section className="mt-3">
            <p className="section-label mb-3">HOW IT WORKS</p>
            <div className="grid grid-cols-[1rem_1fr] gap-x-4">
              <div className="relative">
                <div className="absolute left-[7px] top-1 h-full w-px bg-border-light" />
                {[0, 1, 2, 3].map((item) => (
                  <div key={item} className="relative h-[66px]">
                    <span className="absolute left-[4px] top-1 block h-[6px] w-[6px] border border-ink-primary bg-background" />
                  </div>
                ))}
              </div>
              <div className="space-y-3">
                {[
                  ['UPLOAD', 'Resume and target role are captured.'],
                  ['ANALYSIS', 'Signals and score model are generated.'],
                  ['INTERVIEW', 'Live oral responses are evaluated.'],
                  ['DEBRIEF', 'A printable report closes the loop.'],
                ].map(([step, text]) => (
                  <div key={step} className="h-[66px]">
                    <p className="font-bold">{step}</p>
                    <p className="text-sm" style={{ color: 'var(--ink-secondary)' }}>
                      {text}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </aside>
      </main>
    </div>
  )
}
