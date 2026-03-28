import { StakeholderReport } from '../lib/types'

interface StakeholderReportProps {
  report: StakeholderReport
}

const STAKEHOLDER_LABELS: Record<string, string> = {
  hiring_manager: 'Hiring Manager',
  technical_lead: 'Technical Lead',
  hr_representative: 'HR Representative',
  peer_engineer: 'Peer Engineer',
}

function decisionColor(decision: string): string {
  if (decision === 'hire') {
    return 'var(--positive)'
  }
  if (decision === 'no_hire') {
    return 'var(--concern)'
  }
  return 'var(--ink-secondary)'
}

function titleCase(value: string): string {
  return value.replace(/_/g, ' ').toUpperCase()
}

export default function StakeholderReportView({ report }: StakeholderReportProps) {
  return (
    <div className="mx-auto max-w-6xl border-x border-ink-primary p-6">
      <header className="border-b border-ink-primary pb-4">
        <p className="section-label">STAGE 03</p>
        <h1 className="display-tight mt-1 text-4xl">MULTI-STAKEHOLDER DECISION REPORT</h1>
        <div className="rule-thin my-3" />
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="section-label">CONSENSUS</p>
            <p className="mono-data text-2xl" style={{ color: decisionColor(report.consensus_decision) }}>
              {titleCase(report.consensus_decision)}
            </p>
          </div>
          <div>
            <p className="section-label">CONFIDENCE</p>
            <p className="mono-data text-2xl">{Math.round(report.consensus_confidence)}/100</p>
          </div>
          <div>
            <p className="section-label">AGREEMENT LEVEL</p>
            <p className="mono-data text-2xl">{Math.round(report.consensus_metrics.agreement_level)}/100</p>
          </div>
        </div>
      </header>

      <section className="mt-5">
        <p className="section-label mb-3">INDIVIDUAL DECISIONS</p>
        <div className="grid grid-cols-2 gap-4">
          {report.individual_decisions.map((decision) => (
            <article key={decision.stakeholder_type} className="border border-ink-primary p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="font-bold">{STAKEHOLDER_LABELS[decision.stakeholder_type] || decision.stakeholder_type}</p>
                <div className="text-right">
                  <p className="mono-data text-xs" style={{ color: decisionColor(decision.decision) }}>
                    {titleCase(decision.decision)}
                  </p>
                  <p className="mono-data text-xs">{Math.round(decision.confidence_score)}/100</p>
                </div>
              </div>
              <p className="mt-2 text-sm" style={{ color: 'var(--ink-secondary)' }}>
                {decision.reasoning}
              </p>

              <div className="rule-light my-2" />
              <p className="section-label">KEY STRENGTHS</p>
              {decision.key_strengths.length ? (
                <div className="mt-1 space-y-1">
                  {decision.key_strengths.map((strength, idx) => (
                    <p key={`${decision.stakeholder_type}-strength-${idx}`} className="text-sm">
                      {strength}
                    </p>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-sm italic" style={{ color: 'var(--ink-muted)' }}>
                  No strengths listed.
                </p>
              )}

              <div className="rule-light my-2" />
              <p className="section-label">KEY CONCERNS</p>
              {decision.key_concerns.length ? (
                <div className="mt-1 space-y-1">
                  {decision.key_concerns.map((concern, idx) => (
                    <p key={`${decision.stakeholder_type}-concern-${idx}`} className="text-sm" style={{ color: 'var(--ink-secondary)' }}>
                      {concern}
                    </p>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-sm italic" style={{ color: 'var(--ink-muted)' }}>
                  No concerns listed.
                </p>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="mt-5 border-t-2 border-ink-primary pt-4">
        <p className="section-label mb-2">CONSENSUS DISCUSSION</p>
        <p className="text-sm">{report.consensus_reasoning}</p>
        <div className="mt-3 grid grid-cols-2 gap-5">
          <div>
            <p className="section-label">DISCUSSION POINTS</p>
            {report.consensus_metrics.discussion_points.length ? (
              <div className="mt-1 space-y-1">
                {report.consensus_metrics.discussion_points.map((point, idx) => (
                  <p key={`discussion-${idx}`} className="text-sm" style={{ color: 'var(--ink-secondary)' }}>
                    {point}
                  </p>
                ))}
              </div>
            ) : (
              <p className="mt-1 text-sm italic" style={{ color: 'var(--ink-muted)' }}>
                No discussion points recorded.
              </p>
            )}
          </div>
          <div>
            <p className="section-label">COMPROMISE AREAS</p>
            {report.consensus_metrics.compromise_areas.length ? (
              <div className="mt-1 space-y-1">
                {report.consensus_metrics.compromise_areas.map((area, idx) => (
                  <p key={`compromise-${idx}`} className="text-sm" style={{ color: 'var(--ink-secondary)' }}>
                    {area}
                  </p>
                ))}
              </div>
            ) : (
              <p className="mt-1 text-sm italic" style={{ color: 'var(--ink-muted)' }}>
                No compromise areas identified.
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="mt-5 border-t-2 border-ink-primary pt-4">
        <p className="section-label">FINAL RECOMMENDATION</p>
        <p className="mt-2 text-lg italic" style={{ color: 'var(--ink-secondary)' }}>
          {report.final_recommendation}
        </p>
      </section>
    </div>
  )
}
