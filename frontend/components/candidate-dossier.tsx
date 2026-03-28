'use client'

import { useMemo, useState } from 'react'
import { CandidateProfile } from '../lib/types'

interface CandidateDossierProps {
  profile: CandidateProfile
  targetRole: string
}

function safe(value: string | null | undefined, fallback = 'Not provided'): string {
  return value && value.trim() ? value : fallback
}

export default function CandidateDossier({ profile, targetRole }: CandidateDossierProps) {
  const [expandedSkills, setExpandedSkills] = useState(false)

  const skills = useMemo(() => profile.skills || [], [profile.skills])
  const visibleSkills = expandedSkills ? skills : skills.slice(0, 12)

  return (
    <section className="space-y-4">
      <div>
        <h2 className="display-tight text-[2rem]">{safe(profile.name)}</h2>
        <p className="text-lg italic" style={{ color: 'var(--ink-secondary)' }}>
          {safe(targetRole, 'Role not provided')}
        </p>
      </div>

      <div className="rule-thin" />

      <div className="space-y-2">
        <p className="ui-label text-xs" style={{ color: 'var(--ink-secondary)' }}>
          {[safe(profile.location, 'Unknown location'), safe(profile.email, 'No email')].join(' · ')}
        </p>
        <div className="flex flex-wrap gap-3">
          {profile.github_url ? (
            <a className="section-label hover:underline" href={profile.github_url} rel="noreferrer" target="_blank">
              [GITHUB]
            </a>
          ) : null}
          {profile.linkedin_url ? (
            <a className="section-label hover:underline" href={profile.linkedin_url} rel="noreferrer" target="_blank">
              [LINKEDIN]
            </a>
          ) : null}
          {profile.website_url ? (
            <a className="section-label hover:underline" href={profile.website_url} rel="noreferrer" target="_blank">
              [WEBSITE]
            </a>
          ) : null}
        </div>
      </div>

      <div className="rule-thin" />

      <div>
        <p className="section-label mb-2">SKILLS</p>
        {skills.length ? (
          <p className="mono-data text-sm" style={{ color: 'var(--ink-secondary)' }}>
            {visibleSkills.join(', ')}
            {!expandedSkills && skills.length > 12 ? (
              <>
                {', '}
                <button className="italic underline" onClick={() => setExpandedSkills(true)} type="button">
                  ...and {skills.length - 12} more
                </button>
              </>
            ) : null}
          </p>
        ) : (
          <p className="italic" style={{ color: 'var(--ink-muted)' }}>
            No skill keywords provided.
          </p>
        )}
      </div>

      <div className="rule-thin" />

      {profile.summary ? (
        <div>
          <p className="italic" style={{ color: 'var(--ink-secondary)' }}>
            {profile.summary}
          </p>
        </div>
      ) : (
        <p className="italic" style={{ color: 'var(--ink-muted)' }}>
          Candidate summary not available.
        </p>
      )}

      <div className="rule-thin" />

      <div>
        <p className="section-label mb-3">EXPERIENCE</p>
        <div className="space-y-3">
          {(profile.experience || []).length ? (
            profile.experience.map((experience) => (
              <div key={`${experience.company}-${experience.start}-${experience.title}`} className="space-y-1 pb-2">
                <div className="flex items-start justify-between gap-3">
                  <p className="font-bold">{safe(experience.company)}</p>
                  <p className="mono-data text-xs" style={{ color: 'var(--ink-secondary)' }}>
                    {safe(experience.start, '?')} - {safe(experience.end, 'Present')}
                  </p>
                </div>
                <p className="italic" style={{ color: 'var(--ink-secondary)' }}>
                  {safe(experience.title)}
                </p>
                <div className="rule-light" />
              </div>
            ))
          ) : (
            <p className="italic" style={{ color: 'var(--ink-muted)' }}>
              No work history found.
            </p>
          )}
        </div>
      </div>

      <div className="rule-thin" />

      <div>
        <p className="section-label mb-3">EDUCATION</p>
        <div className="space-y-3">
          {(profile.education || []).length ? (
            profile.education.map((education) => (
              <div key={`${education.institution}-${education.year}`}>
                <div className="flex items-start justify-between gap-3">
                  <p className="font-bold">{safe(education.institution)}</p>
                  <p className="mono-data text-xs" style={{ color: 'var(--ink-secondary)' }}>
                    {safe(education.year)}
                  </p>
                </div>
                <p className="italic" style={{ color: 'var(--ink-secondary)' }}>
                  {safe(education.degree)} in {safe(education.field)}
                </p>
              </div>
            ))
          ) : (
            <p className="italic" style={{ color: 'var(--ink-muted)' }}>
              No education entries found.
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
