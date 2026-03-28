'use client'

import { useMemo, useState } from 'react'
import { DebriefReport } from '../lib/types'
import InterviewTranscript from './interview-transcript'

interface DebriefReportProps {
  report: DebriefReport
  candidateName: string
  targetRole: string
  targetCompany: string
}

function verdictLabel(score: number): string {
  if (score >= 80) {
    return 'Excellent interview performance with strong readiness.'
  }
  if (score >= 60) {
    return 'Promising result with clear improvement opportunities.'
  }
  return 'Development required before high-stakes interview rounds.'
}

function ratingSquares(score: number) {
  const value = Math.max(0, Math.min(10, Math.round(score)))
  return (
    <span className="inline-flex gap-1">
      {Array.from({ length: 10 }).map((_, index) => {
        const filled = index < value
        return (
          <span
            key={`${score}-${index}`}
            style={{
              width: '0.52rem',
              height: '0.52rem',
              border: `1px solid ${filled ? 'var(--ink-primary)' : 'var(--border-light)'}`,
              background: filled ? 'var(--ink-primary)' : 'transparent',
              display: 'inline-block',
            }}
          />
        )
      })}
    </span>
  )
}

export default function DebriefReportView({ report, candidateName, targetRole, targetCompany }: DebriefReportProps) {
  const [showTranscript, setShowTranscript] = useState(false)

  const byPriority = useMemo(() => {
    return {
      high: report.study_recommendations.filter((item) => item.priority === 'high'),
      medium: report.study_recommendations.filter((item) => item.priority === 'medium'),
      low: report.study_recommendations.filter((item) => item.priority === 'low'),
    }
  }, [report.study_recommendations])

  return (
    <div className="print-only-content mx-auto max-w-5xl border-x border-border p-6">
      <header className="border-b border-ink-primary pb-5 text-center">
        <h1 className="display-tight text-4xl">INTERVIEW DEBRIEF REPORT</h1>
        <div className="rule-thin my-3" />
        <p className="italic" style={{ color: 'var(--ink-secondary)' }}>
          {candidateName} · {targetRole} · {targetCompany} ·{' '}
          {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
        </p>
        <div className="rule-thin my-3" />
        <p className="mono-data text-7xl leading-none">{Math.max(0, Math.round(report.overall_score))}</p>
        <p className="mono-data text-lg" style={{ color: 'var(--ink-secondary)' }}>
          /100
        </p>
        <p className="mt-2 text-lg italic font-bold">{verdictLabel(report.overall_score)}</p>
      </header>

      <section className="mt-6 border-t-2 border-ink-primary pt-4">
        <p className="section-label">01 — PERFORMANCE BY PHASE</p>
        <div className="mt-3 grid grid-cols-2 gap-4">
          {[
            ['WARMUP', report.phase_breakdown.warmup],
            ['RESUME DEEP DIVE', report.phase_breakdown.resume_deep_dive],
            ['TECHNICAL', report.phase_breakdown.technical],
            ['CLOSING', report.phase_breakdown.closing],
          ].map(([name, phase]) => {
            const p = phase as { score: number; feedback: string }
            return (
              <article key={name as string} className="border border-border p-3">
                <p className="section-label">{name as string}</p>
                <p className="mono-data mt-1 text-4xl">{Math.round(p.score)}</p>
                <p className="mt-2 text-sm" style={{ color: 'var(--ink-secondary)' }}>
                  {p.feedback || 'No feedback captured for this phase.'}
                </p>
              </article>
            )
          })}
        </div>
      </section>

      <section className="mt-6 border-t-2 border-ink-primary pt-4">
        <p className="section-label">02 — ANSWER BREAKDOWN</p>
        <div className="mt-3 space-y-4">
          {(report.answer_feedback || []).map((entry, index) => (
            <article key={`${entry.question}-${index}`} className="border-b border-muted-rule pb-3">
              <p className="font-bold">Q — {entry.question || 'Question not captured'}</p>
              <p className="mt-1 pl-4 italic" style={{ color: 'var(--ink-secondary)' }}>
                {entry.candidate_answer_summary || 'No candidate summary available.'}
              </p>
              <p className="mono-data mt-2 text-sm">SCORE: {Math.round(entry.score || 0)}/10</p>
              <div className="mt-1">{ratingSquares(entry.score || 0)}</div>
              <p className="section-label mt-2">STRONGER ANSWER:</p>
              <p className="mt-1 text-sm">{entry.stronger_answer_example || 'No stronger answer example provided.'}</p>
              {entry.resume_gap_flagged ? (
                <>
                  <p className="section-label mt-2" style={{ color: 'var(--concern)' }}>
                    RESUME GAP:
                  </p>
                  <p className="text-sm" style={{ color: 'var(--concern)' }}>
                    {entry.resume_gap_note || 'Potential discrepancy detected.'}
                  </p>
                </>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <section className="mt-6 border-t-2 border-ink-primary pt-4">
        <p className="section-label">03 — RESUME VS REALITY</p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full border border-ink-primary border-collapse">
            <thead>
              <tr>
                {['CLAIM', 'DEMONSTRATED', 'VERDICT'].map((heading) => (
                  <th key={heading} className="border border-ink-primary px-2 py-1 text-left section-label">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(report.resume_vs_reality || []).map((row, index) => (
                <tr key={`${row.claim}-${index}`}>
                  <td className="border border-ink-primary px-2 py-1">{row.claim || 'Not available'}</td>
                  <td className="border border-ink-primary px-2 py-1">{row.demonstrated || 'Not available'}</td>
                  <td
                    className="border border-ink-primary px-2 py-1 font-bold"
                    style={{
                      color:
                        row.verdict === 'gap' ? 'var(--concern)' : row.verdict === 'matched' || row.verdict === 'exceeded' ? 'var(--positive)' : 'var(--ink-secondary)',
                    }}
                  >
                    {(row.verdict || 'matched').toUpperCase()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-6 border-t-2 border-ink-primary pt-4">
        <p className="section-label">04 — STUDY RECOMMENDATIONS</p>
        <div className="mt-3 space-y-4">
          {[
            ['HIGH PRIORITY', byPriority.high, 'var(--concern)'],
            ['MEDIUM PRIORITY', byPriority.medium, 'var(--ink-primary)'],
            ['LOW PRIORITY', byPriority.low, 'var(--positive)'],
          ].map(([label, items, color]) => (
            <article key={label as string}>
              <p className="section-label">{label as string}</p>
              <div className="mt-2 space-y-2">
                {(items as Array<{ topic: string; reason: string }>).length ? (
                  (items as Array<{ topic: string; reason: string }>).map((item) => (
                    <div key={`${item.topic}-${item.reason}`} className="border-l-2 pl-3" style={{ borderColor: color as string }}>
                      <p className="font-bold">{item.topic}</p>
                      <p className="text-sm italic" style={{ color: 'var(--ink-secondary)' }}>
                        {item.reason}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="italic" style={{ color: 'var(--ink-muted)' }}>
                    No recommendations in this priority bucket.
                  </p>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-6 border-t-2 border-ink-primary pt-4">
        <button className="w-full text-left" onClick={() => setShowTranscript((prev) => !prev)} type="button">
          <span className="section-label">05 — FULL INTERVIEW TRANSCRIPT</span>{' '}
          <span className="mono-data text-xs">[{showTranscript ? 'COLLAPSE' : 'EXPAND'}]</span>
        </button>

        {showTranscript ? (
          <div className="mt-3 border border-border p-3">
            <InterviewTranscript turns={report.conversation_history || []} />
          </div>
        ) : null}
      </section>
    </div>
  )
}
