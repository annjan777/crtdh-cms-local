import { PageDataProvider } from '../api/data.jsx'
import RichText from '../components/RichText.jsx'
import { useMemo, useRef } from 'react'
import { fetchList, fetchOne } from '../api/client'
import { useApi } from '../hooks/useApi'
import ImpactFigures from '../components/ImpactFigures'
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
  const stages = useObjectiveStages(objectiveRows)

  const { data: slides } = useApi(() => fetchList('/hero-slides/'), [], [])
  const ref = useRef(null)
  usePageMotion(ref, [about, focusAreas, objectiveRows, rawTimeline])
  const heroImage = (slides || []).find((sl) => sl.image)?.image

  return (
    <div ref={ref}>
      <PageHero
        page="about"
        eyebrow="About CRTDH"
        title="About CRTDH"
        description="A DSIR-sponsored initiative at IIT Kharagpur translating research in basic sciences, sensors and digital health into affordable, deployable healthcare technology."
        image={heroImage}
      />
      <ImpactFigures page="about" />

      {!aboutLoading && about?.intro && (
        <section data-block="about.intro" className="ab-intro">
          <div className="container ab-split">
            <div className="ab-split__label">
              <h2 className="section-title">Why CRTDH exists</h2>
            </div>
            <div className="ab-split__body" style={{ '--d': '120ms' }}>
              <ProseBlock text={about.intro} />
            </div>
          </div>
        </section>
      )}

      {!aboutLoading && about?.mission_vision && (
        <section data-block="about.intro" className="ab-mission">
          <div className="container ab-split">
            <div className="ab-split__label">
              <h2 className="ab-mission__title">Our mission</h2>
            </div>
            <div className="ab-split__body ab-mission__body" style={{ '--d': '120ms' }}>
              <ProseBlock text={about.mission_vision} />
            </div>
          </div>
        </section>
      )}

      <section data-block="about.focus" className="ab-focus">
        <div className="container">
          <div className="ab-focus__head">
            <div>
              <h2 className="section-title">Focus areas</h2>
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
                  <li key={area.id} className="focus-chip" style={{ '--chip-color': area.color || 'var(--forest-800)', '--d': `${k * 60}ms` }}>
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
          <div className="ab-journey__head">
            <h2 className="section-title">Healthcare ecosystem at IIT Kharagpur</h2>
          </div>
          <DataState loading={timelineLoading} error={timelineError} data={timeline} emptyProps={{ title: 'Timeline coming soon' }}>
            {(entries) => (
              <ol className="ab-timeline">
                {entries.map((entry, k) => (
                  <li className="ab-timeline__entry" key={entry.id} style={{ '--d': `${k * 120}ms` }}>
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

      <section data-block="about.support" className="ab-support" id="objectives">
        <div className="container">
          <div className="ab-support__head">
            <h2 className="section-title">How CRTDH supports MSMEs</h2>
            <p>Seven stages, from an MSME's idea to its first sales.</p>
          </div>
          <DataState loading={objLoading} error={objError} data={objectiveRows} emptyProps={{ title: 'Objectives coming soon' }}>
            {() => (
              <ol className="ab-process">
                {stages.map((st, k) => (
                  <li className="ab-process__stage" key={st.name}>
                    <span className="ab-process__num" aria-hidden="true">{String(k + 1).padStart(2, '0')}</span>
                    <h3 className="ab-process__name">{st.name}</h3>
                    <div className="ab-process__body">
                      <ul className="ab-process__tasks">{st.tasks.map((t) => <li key={t}>{t}</li>)}</ul>
                      {st.outcomes.length > 0 && (
                        <div className="ab-process__outcome">
                          <h4>Outcome</h4>
                          {st.outcomes.map((o) => <p key={o}>{o}</p>)}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </DataState>
        </div>
      </section>

      {!aboutLoading && ((about?.pi_desk_image && about?.pi_desk_document) || about?.dsir_about || about?.iitkgp_about) && (
        <section data-block="about.partners" className="ab-orgs">
          <div className={`container ab-orgs__grid${about.pi_desk_image && about.pi_desk_document ? '' : ' ab-orgs__grid--two'}`}>
            {/* The PI's note is shown only when its document is in the CMS: the cover image on its own is the
                page title again, with nothing to read behind it. */}
            {about.pi_desk_image && about.pi_desk_document && (
              <figure data-block="about.pi-note" className="ab-pi">
                <span className="eyebrow">From the PI&apos;s desk</span>
                <a href={about.pi_desk_document} target="_blank" rel="noreferrer">
                  <img src={about.pi_desk_image} alt="" loading="lazy" />
                  <span>Read the note from the PI&apos;s desk (PDF)</span>
                </a>
              </figure>
            )}
            {about.dsir_about && (
              <div className="ab-org" style={{ '--d': '100ms' }}>
                <h3>About DSIR, Govt. of India</h3>
                <ProseBlock text={about.dsir_about} />
              </div>
            )}
            {about.iitkgp_about && (
              <div className="ab-org" style={{ '--d': '200ms' }}>
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

// The CMS objectives table as stages: rows grouped by `category` in CMS order. A task or outcome that the
// table repeats (it came from merged cells in the original table) is shown once.
function useObjectiveStages(rows) {
  return useMemo(() => {
    const stages = []
    for (const r of rows || []) {
      const name = (r.category || '').trim()
      if (!name) continue
      let st = stages.find((x) => x.name === name)
      if (!st) stages.push((st = { name, tasks: [], outcomes: [] }))
      const task = (r.task || '').trim()
      const outcome = (r.outcome || '').trim()
      if (task && !st.tasks.includes(task)) st.tasks.push(task)
      if (outcome && !st.outcomes.includes(outcome)) st.outcomes.push(outcome)
    }
    return stages
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
