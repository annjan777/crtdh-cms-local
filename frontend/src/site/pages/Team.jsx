import { PageDataProvider } from '../api/data.jsx'
import { useRef } from 'react'
import { Link } from '../router.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import { DataState, Spinner } from '../components/StateBlock'
import { usePageMotion } from '../components/motion4.js'
import './Team.css'

/*
 * The team as an organisation chart in three tiers, built from the CMS categories (nothing is invented):
 *   1. Leadership: the Principal Investigator, then the Co-Principal Investigators.
 *   2. Research members: categories whose name says research / member / scientist / fellow.
 *   3. Project and support team: every other category (manager, project staff, medical staff...).
 * Within a tier, categories keep their CMS order and members keep their CMS order.
 */
const isPI = (name) => /^principal investigator/i.test(name || '')
const isCoPI = (name) => /co-?\s*principal/i.test(name || '')
const isResearch = (name) => /research|member|scientist|fellow|scholar/i.test(name || '')

// A person's role line: their own designation if the CMS has one, else the category in the singular.
function roleFor(member, categoryName) {
  if (member.designation) return member.designation
  const n = categoryName || ''
  if (/^other members?$/i.test(n)) return 'Research member'
  return n.replace(/s$/, '')
}

function Portrait({ member, lead }) {
  const initials = (member.name || '')
    .replace(/^(prof|dr|mr|ms|mrs)\.?\s+/i, '')
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
  return (
    <span className={`tp${lead ? ' tp--lead' : ''}`}>
      {member.photo ? <img src={member.photo} alt="" loading={lead ? 'eager' : 'lazy'} /> : <span className="tp__initials" aria-hidden="true">{initials}</span>}
    </span>
  )
}

function Person({ m, role, home }) {
  return (
    <li className="tperson">
      <Portrait member={m} />
      <h3 className="tperson__name">{m.name}</h3>
      <p className="tperson__role">{role}</p>
      {/* The institution is shown once, under the PI; repeated only when a member's differs. */}
      {m.institution && m.institution !== home && <p className="tperson__inst">{m.institution}</p>}
      {m.description && <p className="tperson__desc">{m.description}</p>}
      {m.email && <a className="tperson__mail" href={`mailto:${m.email}`}>{m.email}</a>}
    </li>
  )
}

function Tier({ id, title, intro, people, cols, home }) {
  if (!people.length) return null
  return (
    <section className="ttier" aria-labelledby={id}>
      <div className="ttier__head">
        <h2 id={id}>{title}</h2>
        {intro && <p>{intro}</p>}
      </div>
      <ul className={`tgrid tgrid--${cols}`}>
        {people.map(({ m, role }) => <Person key={m.id} m={m} role={role} home={home} />)}
      </ul>
    </section>
  )
}

function Organisation({ categories, members }) {
  const groups = categories
    .map((c) => ({ c, list: members.filter((m) => m.category === c.id) }))
    .filter((g) => g.list.length)
  const piGroup = groups.find((g) => isPI(g.c.name))
  const coGroups = groups.filter((g) => isCoPI(g.c.name))
  const rest = groups.filter((g) => g !== piGroup && !coGroups.includes(g))
  const research = rest.filter((g) => isResearch(g.c.name))
  const support = rest.filter((g) => !isResearch(g.c.name))
  const flat = (gs) => gs.flatMap(({ c, list }) => list.map((m) => ({ m, role: roleFor(m, c.name) })))
  const lead = piGroup?.list[0]
  const home = lead?.institution || ''

  return (
    <>
      {lead && (
        <article className="tlead" aria-labelledby={`tm-${lead.id}`}>
          <div className="tlead__photo" data-rv="mask"><Portrait member={lead} lead /></div>
          <div className="tlead__copy">
            <p className="tlead__role">{roleFor(lead, piGroup.c.name)}</p>
            <h2 className="tlead__name" id={`tm-${lead.id}`}>{lead.name}</h2>
            {lead.institution && <p className="tlead__inst">{lead.institution}</p>}
            {lead.description && <p className="tlead__desc">{lead.description}</p>}
            {lead.email && <a className="tperson__mail" href={`mailto:${lead.email}`}>{lead.email}</a>}
          </div>
          {/* Further PIs, if the CMS ever lists more than one, sit with the Co-PIs below. */}
        </article>
      )}
      <Tier
        id="team-copi"
        title={coGroups.length === 1 && coGroups[0].list.length === 1 ? 'Co-Principal Investigator' : 'Co-Principal Investigators'}
        people={[...flat(piGroup ? [{ c: piGroup.c, list: piGroup.list.slice(1) }] : []), ...flat(coGroups)]}
        cols="3"
        home={home}
      />
      <Tier id="team-research" title="Research members" people={flat(research)} cols="4" home={home} />
      <Tier id="team-support" title="Project and support team" people={flat(support)} cols="4" home={home} />
    </>
  )
}

function TeamView() {
  const { data: categories, loading: catLoading, error: catError } = useApi(() => fetchList('/team-categories/'), [], [])
  const { data: members, loading: memberLoading } = useApi(() => fetchList('/team-members/'), [], [])
  const loading = catLoading || memberLoading
  const ref = useRef(null)
  usePageMotion(ref, [categories, members])

  return (
    <div className="team-page" ref={ref}>
      <PageHero
        page="team"
        eyebrow="Team"
        title="The people behind CRTDH"
        description="Principal investigators, research members, project staff and medical collaborators."
      />
      <section data-block="team.members" className="tm">
        <div className="container">
          {loading ? (
            <Spinner />
          ) : (
            <DataState loading={false} error={catError} data={categories} emptyProps={{ title: 'Team members coming soon' }}>
              {(cats) => <Organisation categories={cats} members={members || []} />}
            </DataState>
          )}
        </div>
      </section>
      <section className="tm-cta">
        <div className="container tm-cta__row">
          <h2 className="tm-cta__title">Want to work with the team?</h2>
          <Link to="/contact" className="tm-cta__link">Write to the centre</Link>
        </div>
      </section>
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Team({ data }) {
  return (
    <PageDataProvider data={data}>
      <TeamView />
    </PageDataProvider>
  )
}
