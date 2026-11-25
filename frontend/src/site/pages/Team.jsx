import { PageDataProvider } from '../api/data.jsx'
import { useRef } from 'react'
import { User, ArrowRight, Mail } from 'lucide-react'
import { Link } from '../router.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import { DataState, Spinner } from '../components/StateBlock'
import { usePageMotion } from '../components/motion4.js'
import './Team.css'

// Singular role label for a member of a category (the CMS stores category names, often plural).
function roleFor(member, categoryName) {
  if (member.designation) return member.designation
  const n = categoryName || ''
  if (/^other members?$/i.test(n)) return 'Research member'
  return n.replace(/s$/, '')
}

function Portrait({ member, size }) {
  return (
    <span className={`tm-portrait tm-portrait--${size}`}>
      {member.photo ? <img src={member.photo} alt="" loading="lazy" /> : <User size={size === 'lead' ? 56 : 32} aria-hidden="true" />}
    </span>
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
              {(cats) => {
                const groups = cats.map((c) => ({ c, list: (members || []).filter((m) => m.category === c.id) })).filter((g) => g.list.length)
                const hasLead = groups[0]?.list.length === 1
                const rendered = groups.map(({ c, list }, gi) => {
                  const lead = gi === 0 && list.length === 1
                  if (lead) {
                    const m = list[0]
                    return (
                      <article className="tm-lead" key={c.id} aria-labelledby={`tm-${m.id}`}>
                        <div className="tm-lead__photo" data-rv="mask"><Portrait member={m} size="lead" /></div>
                        <div className="tm-lead__copy" data-rv style={{ '--d': '150ms' }}>
                          <span className="eyebrow">{c.name}</span>
                          <h2 className="tm-lead__name" id={`tm-${m.id}`}>{m.name}</h2>
                          <p className="tm-lead__role">{m.designation || c.name}{m.institution ? `, ${m.institution}` : ''}</p>
                          {m.description && <p className="tm-lead__desc">{m.description}</p>}
                          {m.email && <a className="tm-mail" href={`mailto:${m.email}`}><Mail size={16} aria-hidden="true" /> {m.email}</a>}
                        </div>
                      </article>
                    )
                  }
                  return (
                    <section className="tm-group" key={c.id} aria-labelledby={`tmc-${c.id}`} style={{ '--n': Math.min(list.length, 4) }}>
                      <div className="tm-group__head" data-rv>
                        <h2 id={`tmc-${c.id}`}>{c.name}</h2>
                        {list.length > 1 && <span className="tm-group__count">{list.length} people</span>}
                      </div>
                      <ul className="tm-grid">
                        {list.map((m, k) => (
                          <li className="tm-person" key={m.id} data-rv="mask" style={{ '--d': `${(k % 4) * 90}ms` }}>
                            <Portrait member={m} size="std" />
                            <h3 className="tm-person__name">{m.name}</h3>
                            <p className="tm-person__role">{roleFor(m, c.name)}</p>
                            {m.institution && <p className="tm-person__inst">{m.institution}</p>}
                            {m.description && <p className="tm-person__desc">{m.description}</p>}
                            {m.email && <a className="tm-mail" href={`mailto:${m.email}`}><Mail size={14} aria-hidden="true" /> Email</a>}
                          </li>
                        ))}
                      </ul>
                    </section>
                  )
                })
                return (
                  <>
                    {hasLead && rendered[0]}
                    <div className="tm-groups">{hasLead ? rendered.slice(1) : rendered}</div>
                  </>
                )
              }}
            </DataState>
          )}
        </div>
      </section>
      <section className="tm-cta">
        <div className="container tm-cta__row" data-rv>
          <h2 className="tm-cta__title">Want to work with the team?</h2>
          <Link to="/contact" className="btn btn--primary">Get in touch <ArrowRight size={17} aria-hidden="true" /></Link>
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
