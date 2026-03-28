interface ThreadObject {
  topic?: string
  questions?: string[]
  rationale?: string
}

interface InterviewThreadsProps {
  threads: Array<string | ThreadObject>
}

function normalizeThreadText(thread: string | ThreadObject): string {
  if (typeof thread === 'string') {
    return thread
  }

  const topic = thread.topic?.trim() || ''
  const firstQuestion = thread.questions?.[0]?.trim() || ''
  const rationale = thread.rationale?.trim() || ''

  if (topic && firstQuestion) {
    return `${topic}: ${firstQuestion}`
  }

  if (topic) {
    return topic
  }

  if (firstQuestion) {
    return firstQuestion
  }

  if (rationale) {
    return rationale
  }

  return 'Thread detail unavailable'
}

export default function InterviewThreads({ threads }: InterviewThreadsProps) {
  const normalizedThreads = threads.map((thread) => normalizeThreadText(thread))

  if (!normalizedThreads.length) {
    return (
      <section>
        <p className="section-label mb-2">FOCUS AREAS</p>
        <p className="mono-data text-sm" style={{ color: 'var(--ink-muted)' }}>
          0 THREADS IDENTIFIED
        </p>
      </section>
    )
  }

  return (
    <section>
      <p className="section-label mb-1">FOCUS AREAS</p>
      <p className="mono-data mb-3 text-sm">{normalizedThreads.length} THREADS IDENTIFIED</p>

      <div className="border-l-2 border-ink-primary pl-3">
        <p>{normalizedThreads[0]}</p>
      </div>

      {normalizedThreads.length > 1 ? (
        <div className="relative mt-3 border border-dashed border-ink-primary p-3">
          <div style={{ filter: 'blur(4px)', userSelect: 'none', pointerEvents: 'none' }}>
            <div className="space-y-2">
              {normalizedThreads.slice(1).map((thread, index) => (
                <div key={`${thread}-${index}`} className="border-l-2 border-ink-primary pl-3">
                  <p>{thread}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="section-label" style={{ color: 'var(--ink-primary)' }}>
              ⬤ REVEALED DURING INTERVIEW
            </p>
          </div>
        </div>
      ) : null}
    </section>
  )
}
