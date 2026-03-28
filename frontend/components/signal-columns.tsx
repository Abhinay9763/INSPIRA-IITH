interface SignalColumnsProps {
  strongSignals: string[]
  weakSignals: string[]
}

const SCORING_GUIDE = [
  ['Technical Skills', 'Depth of engineering understanding and problem solving.'],
  ['Project Quality', 'Originality and practical complexity across shipped work.'],
  ['GitHub Activity', 'Consistency of contribution and collaboration habits.'],
  ['Experience Depth', 'Ownership scope and progression over time.'],
  ['Communication', 'Clarity in explanation, structure, and tradeoff reasoning.'],
]

export default function SignalColumns({ strongSignals, weakSignals }: SignalColumnsProps) {
  return (
    <section className="space-y-4">
      <div>
        <p className="section-label mb-2">STRENGTHS</p>
        {strongSignals.length ? (
          <div className="space-y-2">
            {strongSignals.map((signal) => (
              <div key={signal} className="border-l-2 border-positive pl-3">
                <p>{signal}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="italic" style={{ color: 'var(--ink-muted)' }}>
            NO STRONG SIGNALS DETECTED
          </p>
        )}
      </div>

      <div className="rule-thin" />

      <div>
        <p className="section-label mb-2">CONCERNS</p>
        {weakSignals.length ? (
          <div className="space-y-2">
            {weakSignals.map((signal) => (
              <div key={signal} className="border-l-2 border-concern pl-3">
                <p style={{ color: 'var(--ink-secondary)' }}>{signal}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="italic" style={{ color: 'var(--ink-muted)' }}>
            NO CONCERNS DETECTED
          </p>
        )}
      </div>

      <div className="rule-thin" />

      <div>
        <p className="section-label mb-2">SCORING GUIDE</p>
        <div className="space-y-2">
          {SCORING_GUIDE.map(([dimension, text]) => (
            <div key={dimension} className="grid grid-cols-[9rem_1fr] gap-2">
              <p className="ui-label text-xs" style={{ color: 'var(--ink-secondary)' }}>
                {dimension}
              </p>
              <p className="ui-label text-xs" style={{ color: 'var(--ink-muted)' }}>
                {text}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
