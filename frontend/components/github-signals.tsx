import { GitHubSignals, Repository } from '../lib/types'

interface GitHubSignalsProps {
  signals?: GitHubSignals | null
  candidateGithubUrl?: string | null
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

export default function GitHubSignalsSection({ signals, candidateGithubUrl }: GitHubSignalsProps) {
  const hasGithubAnalysis = Boolean(signals?.username)
  const hasGithubOnResume = Boolean(candidateGithubUrl && String(candidateGithubUrl).trim())
  const resolvedSignals = signals || null

  return (
    <section>
      <p className="section-label mb-3">GITHUB ANALYSIS</p>

      {!hasGithubAnalysis ? (
        <div>
          <p className="italic" style={{ color: 'var(--ink-muted)' }}>
            {hasGithubOnResume ? 'GITHUB ANALYSIS UNAVAILABLE' : 'NO GITHUB PROFILE DETECTED'}
          </p>
          <p className="ui-label mt-2 text-xs" style={{ color: 'var(--ink-secondary)' }}>
            {hasGithubOnResume
              ? 'A GitHub URL was found in the resume, but repository signals could not be fetched for this run.'
              : 'GitHub activity score may be lower due to missing profile context.'}
          </p>
          {hasGithubOnResume ? (
            <a className="section-label mt-2 inline-block hover:underline" href={candidateGithubUrl || '#'} rel="noreferrer" target="_blank">
              [OPEN PROFILE]
            </a>
          ) : null}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3 pb-3">
            <StatCell label="REPOS" value={resolvedSignals?.public_repos || 0} withDivider />
            <StatCell label="FOLLOWERS" value={resolvedSignals?.followers || 0} withDivider />
            <StatCell label="STARS" value={resolvedSignals?.total_stars || 0} withDivider={false} />
          </div>

          <div className="rule-thin" />

          <div className="space-y-3 pt-3">
            {(resolvedSignals?.repositories || []).slice(0, 5).map((repo) => {
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
