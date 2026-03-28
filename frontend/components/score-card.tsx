import { ScoreBreakdown } from '../lib/types'

interface ScoreCardProps {
  scoreBreakdown: ScoreBreakdown
}

const DIMENSIONS: Array<{ key: keyof Omit<ScoreBreakdown, 'overall_score'>; label: string }> = [
  { key: 'technical_skills', label: 'TECHNICAL SKILLS' },
  { key: 'project_quality', label: 'PROJECT QUALITY' },
  { key: 'github_activity', label: 'GITHUB ACTIVITY' },
  { key: 'experience_depth', label: 'EXPERIENCE DEPTH' },
  { key: 'communication', label: 'COMMUNICATION' },
]

function interpretation(score: number): string {
  if (score >= 35) {
    return 'STRONG CANDIDATE'
  }

  if (score >= 20) {
    return 'MODERATE FIT'
  }

  return 'NEEDS DEVELOPMENT'
}

function clampScore(value: number): number {
  if (Number.isNaN(value)) {
    return 0
  }

  return Math.max(0, Math.min(10, Math.round(value)))
}

function renderSquares(score: number): JSX.Element {
  const clamped = clampScore(score)

  return (
    <span className="mt-1 inline-flex gap-1">
      {Array.from({ length: 10 }).map((_, index) => {
        const filled = index < clamped
        return (
          <span
            key={`${score}-${index}`}
            style={{
              display: 'inline-block',
              width: '0.58rem',
              height: '0.58rem',
              border: `1px solid ${filled ? 'var(--ink-primary)' : 'var(--border-light)'}`,
              background: filled ? 'var(--ink-primary)' : 'transparent',
            }}
          />
        )
      })}
    </span>
  )
}

function ScoreRing({ score }: { score: number }) {
  const normalized = Math.max(0, Math.min(50, Math.round(score)))
  const radius = 36
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (normalized / 50) * circumference

  return (
    <svg width="92" height="92" viewBox="0 0 92 92" role="img" aria-label="Overall score ring">
      <circle cx="46" cy="46" r={radius} fill="none" stroke="var(--border-light)" strokeWidth="1" />
      <circle
        cx="46"
        cy="46"
        r={radius}
        fill="none"
        stroke="var(--ink-primary)"
        strokeWidth="2"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform="rotate(-90 46 46)"
      />
    </svg>
  )
}

export default function ScoreCard({ scoreBreakdown }: ScoreCardProps) {
  const overall = Math.max(0, Math.min(50, Math.round(scoreBreakdown.overall_score || 0)))

  return (
    <section>
      <p className="section-label mb-3">EVALUATION</p>

      <div className="mb-4 flex items-center justify-between gap-3 border-b border-muted-rule pb-4">
        <div>
          <p className="mono-data text-6xl leading-none">{overall}</p>
          <p className="mono-data text-base" style={{ color: 'var(--ink-secondary)' }}>
            /50
          </p>
          <p className="section-label mt-2" style={{ color: 'var(--ink-primary)' }}>
            {interpretation(overall)}
          </p>
        </div>
        <ScoreRing score={overall} />
      </div>

      <div className="space-y-4">
        {DIMENSIONS.map((dimension) => {
          const value = scoreBreakdown[dimension.key] || 0
          return (
            <div key={dimension.key}>
              <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3">
                <p className="section-label">{dimension.label}</p>
                <span className="dot-leaders" />
                <p className="mono-data text-sm">{clampScore(value)}/10</p>
              </div>
              {renderSquares(value)}
            </div>
          )
        })}
      </div>
    </section>
  )
}
