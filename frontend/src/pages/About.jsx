import { useMemo } from 'react'
import { fetchList, fetchOne } from '../api/client'
import { useApi } from '../hooks/useApi'
import PageHero from '../components/PageHero'
import { DataState } from '../components/StateBlock'
import Reveal, { Stagger, StaggerItem } from '../components/Reveal'
import './About.css'

export default function About() {
  const { data: about, loading: aboutLoading } = useApi(() => fetchOne('/about-page/'), [], null)
  const { data: focusAreas, loading: focusLoading, error: focusError } = useApi(
    () => fetchList('/focus-areas/'),
    [],
    [],
  )
  const { data: objectiveRows, loading: objLoading, error: objError } = useApi(
    () => fetchList('/objective-rows/'),
    [],
    [],
  )
  const { data: timeline, loading: timelineLoading, error: timelineError } = useApi(
    () => fetchList('/timeline-entries/'),
    [],
    [],
  )

  const focusTaglines = (about?.focus_intro || '').split('\n').filter(Boolean)
  const groupedObjectives = useGroupedObjectives(objectiveRows)

  return (
    <div>
      <PageHero
        eyebrow="About CRTDH"
        title="Mission &amp; Vision"
        description="A DSIR-sponsored initiative at IIT Kharagpur translating research in basic sciences, sensors and digital health into affordable, deployable healthcare technology."
      />

      {!aboutLoading && about?.intro && (
        <section className="section">
          <div className="container container--narrow">
            <Reveal className="section-head text-center" style={{ margin: '0 auto var(--space-6)' }}>
              <span className="eyebrow">About CRTDH</span>
            </Reveal>
            <Reveal delay={0.08}>
              <ProseBlock text={about.intro} />
            </Reveal>
          </div>
        </section>
      )}

      {!aboutLoading && about?.mission_vision && (
        <section className="section section--alt">
          <div className="container container--narrow">
            <Reveal className="section-head text-center" style={{ margin: '0 auto var(--space-6)' }}>
              <span className="eyebrow">Mission &amp; Vision</span>
            </Reveal>
            <Reveal delay={0.08}>
              <ProseBlock text={about.mission_vision} />
            </Reveal>
          </div>
        </section>
      )}

      <section className="section">
        <div className="container">
          <Reveal className="section-head text-center" style={{ margin: '0 auto var(--space-6)' }}>
            <span className="eyebrow">Focus areas</span>
            <h2 className="section-title">Where we work</h2>
            {focusTaglines.map((line) => (
              <p className="focus-tagline" key={line}>
                {line}
              </p>
            ))}
          </Reveal>
          <DataState
            loading={focusLoading}
            error={focusError}
            data={focusAreas}
            emptyProps={{ title: 'Focus areas coming soon' }}
          >
            {(areas) => (
              <Stagger as="ul" className="focus-grid">
                {areas.map((area) => (
                  <StaggerItem
                    as="li"
                    key={area.id}
                    className="focus-chip"
                    style={{ '--chip-color': area.color || 'var(--brand-primary)' }}
                  >
                    {area.title}
                  </StaggerItem>
                ))}
              </Stagger>
            )}
          </DataState>
        </div>
      </section>

      <section className="section section--alt">
        <div className="container">
          <Reveal className="section-head">
            <span className="eyebrow">Objectives</span>
            <h2 className="section-title">How CRTDH supports MSMEs</h2>
          </Reveal>
          <DataState
            loading={objLoading}
            error={objError}
            data={objectiveRows}
            emptyProps={{ title: 'Objectives coming soon' }}
          >
            {() => (
              <Reveal delay={0.1} className="table-wrap card">
                <table className="objective-table">
                  <thead>
                    <tr>
                      <th>Stage</th>
                      <th>Task</th>
                      <th>Outcome</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groupedObjectives.map((row) => (
                      <tr key={row.id}>
                        {row.showCategory && <th rowSpan={row.span} scope="row">{row.category}</th>}
                        <td>{row.task}</td>
                        <td>{row.outcome || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Reveal>
            )}
          </DataState>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <Reveal className="section-head text-center" style={{ margin: '0 auto var(--space-7)' }}>
            <span className="eyebrow">Journey</span>
            <h2 className="section-title">Healthcare ecosystem at IIT Kharagpur</h2>
          </Reveal>
          <DataState
            loading={timelineLoading}
            error={timelineError}
            data={timeline}
            emptyProps={{ title: 'Timeline coming soon' }}
          >
            {(entries) => (
              <Stagger as="ol" className="timeline" stagger={0.12}>
                {entries.map((entry) => (
                  <StaggerItem as="li" className="timeline__entry" key={entry.id}>
                    <div className="timeline__marker">{entry.year}</div>
                    <div className="timeline__body card">
                      {entry.image && <img src={entry.image} alt="" loading="lazy" />}
                      <h3>{entry.title}</h3>
                    </div>
                  </StaggerItem>
                ))}
              </Stagger>
            )}
          </DataState>

          {!aboutLoading && about?.ecosystem_image && (
            <Reveal delay={0.15} className="ecosystem-panel card">
              <img src={about.ecosystem_image} alt="" loading="lazy" />
              {about.ecosystem_heading && <p>{about.ecosystem_heading}</p>}
            </Reveal>
          )}
        </div>
      </section>

      {!aboutLoading && about?.pi_desk_image && (
        <section className="section section--alt">
          <div className="container container--narrow">
            <Reveal className="section-head text-center" style={{ margin: '0 auto var(--space-6)' }}>
              <span className="eyebrow">From the PI's desk</span>
              <h2 className="section-title">A note from our Principal Investigator</h2>
            </Reveal>
            <Reveal delay={0.1} className="pi-desk card">
              <img src={about.pi_desk_image} alt="Note from the PI's desk" loading="lazy" />
            </Reveal>
          </div>
        </section>
      )}

      {!aboutLoading && (about?.dsir_about || about?.iitkgp_about) && (
        <section className="section">
          <div className="container">
            <div className="about-orgs">
              {about.dsir_about && (
                <Reveal className="card about-orgs__card">
                  <h3>About DSIR, Govt. of India</h3>
                  <ProseBlock text={about.dsir_about} />
                </Reveal>
              )}
              {about.iitkgp_about && (
                <Reveal delay={0.1} className="card about-orgs__card">
                  <h3>About IIT Kharagpur</h3>
                  <ProseBlock text={about.iitkgp_about} />
                </Reveal>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

function ProseBlock({ text }) {
  const paragraphs = text.split(/\n{2,}/).filter(Boolean)
  return (
    <div className="prose-block">
      {paragraphs.map((p, i) => (
        <p key={i}>{p}</p>
      ))}
    </div>
  )
}

// The Objectives table groups rows under a shared row-header (rowSpan) by
// `category`, matching the original site's table layout.
function useGroupedObjectives(rows) {
  return useMemo(() => {
    if (!rows) return []
    const spans = {}
    rows.forEach((r) => {
      const key = r.category || `__row-${r.id}`
      spans[key] = (spans[key] || 0) + 1
    })
    const seen = new Set()
    return rows.map((r) => {
      const key = r.category || `__row-${r.id}`
      const first = !seen.has(key)
      seen.add(key)
      return { ...r, showCategory: first, span: spans[key] }
    })
  }, [rows])
}
