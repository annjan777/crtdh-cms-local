import PageShell from '../components/PageShell.jsx'
import { PageBanner } from '../components/Blocks.jsx'
import SiteLink from '../link.jsx'
import { Img } from '../media.jsx'
import { visible } from '../util.js'

/** Team (listing pattern): one section per category, 4:5 portraits, real people only. */
export default function Team({ data }) {
  const c = data.collections || {}
  const members = visible(c['team-members'])
  const groups = (c['team-categories'] || [])
    .map((cat) => ({ ...cat, members: members.filter((m) => m.category === cat.id) }))
    .filter((g) => g.members.length)

  return (
    <PageShell data={data} className="team">
      <PageBanner title="Our team" intro="The people behind CRTDH: principal investigators, project staff and medical collaborators." />
      {groups.length > 0 && (
        <section className="section" aria-label="Team members">
          <div className="wrap team__groups">
            {groups.map((g) => (
              <section key={g.id} className="team__group" aria-labelledby={`team-cat-${g.id}`}>
                <h2 id={`team-cat-${g.id}`} className="team__cat">{g.name}</h2>
                <ul className="people">
                  {g.members.map((m) => (
                    <li key={m.id} className="person">
                      {m.photo ? (
                        <Img src={m.photo} alt={`Portrait of ${m.name}`} ratio="4x5" sizes="(min-width: 1024px) 22vw, (min-width: 768px) 30vw, 45vw" />
                      ) : (
                        <div className="img r-4x5 person__nophoto" aria-hidden="true" />
                      )}
                      <h3 className="person__name">{m.name}</h3>
                      {m.designation && <p className="person__role">{m.designation}</p>}
                      {m.institution && <p className="person__inst soft">{m.institution}</p>}
                      {m.description && <p className="person__desc">{m.description}</p>}
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </section>
      )}
      <section className="section section--surface" aria-labelledby="team-cta">
        <div className="wrap closing">
          <h2 id="team-cta">Work with the team</h2>
          <p className="lead">Researchers, clinicians and enterprises can reach the centre through the contact page.</p>
          <div className="actions">
            <SiteLink to="/contact" className="btn btn--primary">Contact CRTDH</SiteLink>
          </div>
        </div>
      </section>
    </PageShell>
  )
}
