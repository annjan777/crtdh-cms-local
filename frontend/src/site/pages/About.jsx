import PageShell from '../components/PageShell.jsx'
import { PageBanner, Prose } from '../components/Blocks.jsx'
import { Img } from '../media.jsx'

/** About (detail pattern): one reading column, with a facts column where it helps. */
export default function About({ data }) {
  const about = data.singletons?.['about-page'] || {}
  const c = data.collections || {}
  const focus = c['focus-areas'] || []
  const objectives = groupRows(c['objective-rows'] || [])
  const timeline = dedupeTimeline(c['timeline-entries'] || [])
  const taglines = String(about.focus_intro || '').split('\n').map((l) => l.trim()).filter(Boolean)

  return (
    <PageShell data={data} className="about">
      <PageBanner
        title="About CRTDH"
        intro="A DSIR-sponsored centre at IIT Kharagpur translating research in basic sciences, sensors and digital health into affordable, deployable healthcare technology."
      />

      {about.intro && (
        <section className="section" aria-labelledby="about-programme">
          <div className="wrap split">
            <div className="split__main">
              <h2 id="about-programme">The CRTDH programme</h2>
              <Prose text={about.intro} />
            </div>
            {about.ecosystem_image && (
              <figure className="split__side">
                <Img src={about.ecosystem_image} alt={about.ecosystem_heading || ''} ratio={null} contain sizes="(min-width: 768px) 30vw, 100vw" />
                {about.ecosystem_heading && <figcaption>{about.ecosystem_heading}</figcaption>}
              </figure>
            )}
          </div>
        </section>
      )}

      {about.mission_vision && (
        <section className="section section--surface" aria-labelledby="about-mission">
          <div className="wrap">
            <h2 id="about-mission">Mission and vision</h2>
            <Prose text={about.mission_vision} className="mt-6" />
          </div>
        </section>
      )}

      {focus.length > 0 && (
        <section className="section" aria-labelledby="about-focus">
          <div className="wrap grid12">
            <div className="col-head">
              <h2 id="about-focus">Where we work</h2>
              {taglines.map((t) => (
                <p className="soft mt-4" key={t}>{t}</p>
              ))}
            </div>
            <ul className="names names--focus col-body">
              {focus.map((f) => (
                <li key={f.id}>{f.title}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {objectives.length > 0 && (
        <section className="section section--surface" aria-labelledby="about-objectives">
          <div className="wrap">
            <div className="section-head">
              <h2 id="about-objectives">How CRTDH supports MSMEs</h2>
            </div>
            <div className="table-wrap" role="region" aria-labelledby="about-objectives" tabIndex={0}>
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Stage</th>
                    <th scope="col">Task</th>
                    <th scope="col">Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {objectives.map((r) => (
                    <tr key={r.id} className={r.first ? 'is-group-start' : undefined}>
                      {r.first && (
                        <th scope="rowgroup" rowSpan={r.span}>
                          {r.category}
                        </th>
                      )}
                      <td data-label="Task">{r.task}</td>
                      <td data-label="Outcome">{r.outcome || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {timeline.length > 0 && (
        <section className="section" aria-labelledby="about-timeline">
          <div className="wrap">
            <div className="section-head">
              <h2 id="about-timeline">The healthcare ecosystem at IIT Kharagpur</h2>
            </div>
            <ol className="timeline">
              {timeline.map((t) => (
                <li key={t.id}>
                  <p className="timeline__year">{t.year}</p>
                  {t.image && <Img src={t.image} alt="" ratio="3x2" sizes="(min-width: 768px) 30vw, 100vw" />}
                  <h3>{t.title}</h3>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}

      {about.pi_desk_image && (
        <section className="section section--surface" aria-labelledby="about-pi">
          <div className="wrap split split--reverse">
            <div className="split__main">
              <h2 id="about-pi">From the Principal Investigator’s desk</h2>
              {about.pi_desk_document && (
                <p className="mt-6">
                  <a href={about.pi_desk_document} className="text-link" download>Read the note (PDF)</a>
                </p>
              )}
            </div>
            <figure className="split__side split__side--wide">
              <Img src={about.pi_desk_image} alt="Note from the Principal Investigator’s desk" ratio={null} contain sizes="(min-width: 768px) 50vw, 100vw" />
            </figure>
          </div>
        </section>
      )}

      {(about.dsir_about || about.iitkgp_about) && (
        <section className="section" aria-labelledby="about-orgs">
          <div className="wrap">
            <h2 id="about-orgs" className="visually-hidden">The institutions behind CRTDH</h2>
            <div className="two-col">
              {about.dsir_about && (
                <div>
                  <h3>DSIR, Government of India</h3>
                  <Prose text={about.dsir_about} className="mt-4" />
                </div>
              )}
              {about.iitkgp_about && (
                <div>
                  <h3>IIT Kharagpur</h3>
                  <Prose text={about.iitkgp_about} className="mt-4" />
                </div>
              )}
            </div>
          </div>
        </section>
      )}
    </PageShell>
  )
}

function groupRows(rows) {
  const spans = {}
  rows.forEach((r) => {
    const k = r.category || `row-${r.id}`
    spans[k] = (spans[k] || 0) + 1
  })
  const seen = new Set()
  return rows.map((r) => {
    const k = r.category || `row-${r.id}`
    const first = !seen.has(k)
    seen.add(k)
    return { ...r, first, span: spans[k] }
  })
}

function dedupeTimeline(rows) {
  const seen = new Set()
  return rows.filter((t) => {
    const k = `${t.year}-${(t.title || '').trim()}`
    if (seen.has(k)) return false
    seen.add(k)
    return true
  })
}
