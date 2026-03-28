interface ProgressStepsProps {
  currentStep: number
}

const STEPS = [
  'Parsing resume content',
  'Extracting GitHub intelligence',
  'Scoring technical dimensions',
  'Preparing interview threads',
]

export default function ProgressSteps({ currentStep }: ProgressStepsProps) {
  return (
    <section>
      <p className="section-label mb-4">ANALYZING YOUR PROFILE</p>
      <div className="space-y-3 border-y border-muted-rule py-4">
        {STEPS.map((step, index) => {
          const row = index + 1
          const isActive = currentStep === row
          const isDone = currentStep > row

          return (
            <div key={step} className="grid grid-cols-[3rem_1fr_auto] items-center gap-3">
              <span className="mono-data text-sm">{String(row).padStart(2, '0')}</span>
              <span
                className={[
                  'text-base',
                  isActive ? 'cursor-blink font-bold text-ink-primary' : '',
                  isDone ? 'text-ink-muted' : '',
                  !isActive && !isDone ? 'text-ink-secondary' : '',
                ].join(' ')}
              >
                {step}
              </span>
              <span className="mono-data text-sm" style={{ color: isDone ? 'var(--ink-muted)' : 'var(--ink-secondary)' }}>
                {isDone ? '✓' : isActive ? 'LIVE' : 'PENDING'}
              </span>
            </div>
          )
        })}
      </div>
    </section>
  )
}
