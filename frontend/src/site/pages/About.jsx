import { PageDataProvider } from '../api/data.jsx'
import RichText from '../components/RichText.jsx'
import { useMemo, useRef } from 'react'
import { fetchList, fetchOne } from '../api/client'
import { useApi } from '../hooks/useApi'
import PageHero from '../components/PageHero'
import { DataState } from '../components/StateBlock'
import { usePageMotion } from '../components/motion4.js'
import './About.css'

function AboutView() {
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
  const { data: rawTimeline, loading: timelineLoading, error: timelineError } = useApi(
    () => fetchList('/timeline-entries/'),
    [],
    [],
  )

  const timeline = useMemo(() => {
    if (!rawTimeline) return []
    const seen = new Set()
    return rawTimeline.filter(entry => {
      const key = `${entry.year}-${entry.title.trim()}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }, [rawTimeline])

  const focusTaglines = (about?.focus_intro || '').split('\n').filter(Boolean)
  const groupedObjectives = useGroupedObjectives(objectiveRows)

  const { data: slides } = useApi(() => fetchList('/hero-slides/'), [], [])
  const ref = useRef(null)
  usePageMotion(ref, [about, focusAreas, objectiveRows, rawTimeline])
  const heroImage = (slides || []).find((sl) => sl.image)?.image

  return (
    <div ref={ref}>
      <PageHero
        eyebrow="About CRTDH"
        title="About CRTDH"
        description="A DSIR-sponsored initiative at IIT Kharagpur translating research in basic sciences, sensors and digital health into affordable, deployable healthcare technology."
        image={heroImage}
      />

      {!aboutLoading && about?.intro && (
        <section data-block="about.intro" className="ab-intro">
          <div className="container ab-split">
            <div className="ab-split__label" data-rv>
              <span className="eyebrow">Why CRTDH</span>
              <h2 className="section-title">Why CRTDH exists</h2>
            </div>
            <div className="ab-split__body" data-rv style={{ '--d': '120ms' }}>
              <ProseBlock text={about.intro} />
            </div>
          </div>
        </section>
      )}

      {!aboutLoading && about?.mission_vision && (
        <section data-block="about.intro" className="ab-mission">
          <div className="container ab-split">
            <div className="ab-split__label" data-rv>
              <span className="eyebrow eyebrow--on-dark">Mission &amp; vision</span>
              <h2 className="ab-mission__title">Our mission</h2>
            </div>
            <div className="ab-split__body ab-mission__body" data-rv style={{ '--d': '120ms' }}>
              <ProseBlock text={about.mission_vision} />
            </div>
          </div>
        </section>
      )}

      <section data-block="about.focus" className="ab-focus">
        <div className="container">
          <div className="ab-focus__head" data-rv>
            <div>
              <span className="eyebrow">Focus areas</span>
              <h2 className="section-title">Where we work</h2>
            </div>
            {focusTaglines.length > 0 && (
              <div className="ab-focus__taglines">
                {focusTaglines.map((line) => <p className="focus-tagline" key={line}>{line}</p>)}
              </div>
            )}
          </div>
          <DataState loading={focusLoading} error={focusError} data={focusAreas} emptyProps={{ title: 'Focus areas coming soon' }}>
            {(areas) => (
              <ul className="focus-grid">
                {areas.map((area, k) => (
                  <li key={area.id} className="focus-chip" data-rv style={{ '--chip-color': area.color || 'var(--forest-800)', '--d': `${k * 60}ms` }}>
                    {area.title}
                  </li>
                ))}
              </ul>
            )}
          </DataState>
        </div>
      </section>

      <section data-block="about.timeline" className="ab-journey">
        <div className="container ab-journey__grid">
          <div className="ab-journey__head" data-rv>
            <span className="eyebrow">Journey</span>
            <h2 className="section-title">Healthcare ecosystem at IIT Kharagpur</h2>
          </div>
          <DataState loading={timelineLoading} error={timelineError} data={timeline} emptyProps={{ title: 'Timeline coming soon' }}>
            {(entries) => (
              <ol className="ab-timeline">
                {entries.map((entry, k) => (
                  <li className="ab-timeline__entry" key={entry.id} data-rv style={{ '--d': `${k * 120}ms` }}>
                    <span className="ab-timeline__year">{entry.year}</span>
                    <div className="ab-timeline__body">
                      <h3>{entry.title}</h3>
                      {entry.image && <img src={entry.image} alt="" loading="lazy" />}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </DataState>
        </div>
        {!aboutLoading && about?.ecosystem_image && (
          <div className="container">
            <figure data-block="about.ecosystem" className="ab-eco" data-rv="wipe">
              <img src={about.ecosystem_image} alt={about.ecosystem_heading || 'Healthcare ecosystem at IIT Kharagpur'} loading="lazy" />
              {about.ecosystem_heading && <figcaption>{about.ecosystem_heading}</figcaption>}
            </figure>
          </div>
        )}
      </section>

      <section data-block="about.support" className="ab-support">
        <div className="container">
          <div className="ab-support__head" data-rv>
            <span className="eyebrow">Objectives</span>
            <h2 className="section-title">How CRTDH supports MSMEs</h2>
          </div>
          <DataState loading={objLoading} error={objError} data={objectiveRows} emptyProps={{ title: 'Objectives coming soon' }}>
            {() => (
              <div className="table-wrap card" tabIndex={0} role="region" aria-label="How CRTDH supports MSMEs (table, scrolls sideways on small screens)" data-rv>
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
              </div>
            )}
          </DataState>
        </div>
      </section>

      {!aboutLoading && (about?.pi_desk_image || about?.dsir_about || about?.iitkgp_about) && (
        <section data-block="about.partners" className="ab-orgs">
          <div className="container ab-orgs__grid">
            {about.pi_desk_image && (
              <figure data-block="about.pi-note" className="ab-pi" data-rv>
                <span className="eyebrow">From the PI&apos;s desk</span>
                <img src={about.pi_desk_image} alt="Note from the PI's desk" loading="lazy" />
              </figure>
            )}
            {about.dsir_about && (
              <div className="ab-org" data-rv style={{ '--d': '100ms' }}>
                <h3>About DSIR, Govt. of India</h3>
                <ProseBlock text={about.dsir_about} />
              </div>
            )}
            {about.iitkgp_about && (
              <div className="ab-org" data-rv style={{ '--d': '200ms' }}>
                <h3>About IIT Kharagpur</h3>
                <ProseBlock text={about.iitkgp_about} />
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  )
}

function ProseBlock({ text }) {
  return <RichText html={text} className="prose-block" />
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

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function About({ data }) {
  return (
    <PageDataProvider data={data}>
      <AboutView />
    </PageDataProvider>
  )
}
