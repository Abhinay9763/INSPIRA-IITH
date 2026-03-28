import { GitHubSignals, Repository } from '../lib/types'

interface GitHubSignalsProps {
  signals: GitHubSignals
}

function originalityStyle(originality: Repository['originality']): { color: string; label: string } {
  if (originality === 'original') {
    return { color: 'var(--positive)', label: '[ORIGINAL]' }
  }

  if (originality === 'clone') {
    return { color: 'var(--concern)', label: '[CLONE]' }
  }

  if (originality === 'tutorial') {
    return { color: 'var(--ink-muted)', label: '[TUTORIAL]' }
  }

  return { color: 'var(--ink-muted)', label: '[BOILERPLATE]' }
}

function StatCell({ label, value, withDivider }: { label: string; value: number; withDivider: boolean }) {
  return (
    <div className={`text-center ${withDivider ? 'border-r border-border-light' : ''}`}>
      <p className="mono-data text-3xl leading-none">{Math.max(0, Math.round(value || 0))}</p>
      <p className="section-label mt-1">{label}</p>
    </div>
  )
}

export default function GitHubSignalsSection({ signals }: GitHubSignalsProps) {
  const hasGithub = Boolean(signals?.username)

  return (
    <section>
      <p className="section-label mb-3">GITHUB ANALYSIS</p>

      {!hasGithub ? (
        <div>
          <p className="italic" style={{ color: 'var(--ink-muted)' }}>
            NO GITHUB PROFILE DETECTED
          </p>
          <p className="ui-label mt-2 text-xs" style={{ color: 'var(--ink-secondary)' }}>
            GitHub activity score may be lower due to missing profile context.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3 pb-3">
            <StatCell label="REPOS" value={signals.public_repos} withDivider />
            <StatCell label="FOLLOWERS" value={signals.followers} withDivider />
            <StatCell label="STARS" value={signals.total_stars} withDivider={false} />
          </div>

          <div className="rule-thin" />

          <div className="space-y-3 pt-3">
            {(signals.repositories || []).slice(0, 5).map((repo) => {
              const orig = originalityStyle(repo.originality)
              return (
                <div key={repo.url || repo.name} className="pb-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="mono-data text-sm font-bold">{repo.name || 'Unnamed repository'}</p>
                    <div className="flex items-center gap-2">
                      <span
                        className="ui-label px-2 py-[1px] text-[10px]"
                        style={{ border: '1px solid var(--ink-primary)', borderRadius: '2px' }}
                      >
                        {(repo.language || 'Unknown').toUpperCase()}
                      </span>
                      <span className="mono-data text-xs">★ {Math.max(0, Math.round(repo.stars || 0))}</span>
                    </div>
                  </div>

                  <div className="mt-1 grid grid-cols-[auto_1fr_auto] items-center gap-2">
                    <span className="section-label">README SCORE</span>
                    <span className="dot-leaders" />
                    <span className="mono-data text-xs">{Math.max(0, Math.round(repo.readme_score || 0))}/10</span>
                  </div>

                  <p className="section-label mt-1" style={{ color: orig.color }}>
                    {orig.label}
                  </p>

                  <div className="rule-light mt-2" />
                </div>
              )
            })}
          </div>
        </>
      )}
    </section>
  )
}
