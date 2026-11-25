import { useMemo, useState } from 'react'
import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import { ArrowRight } from 'lucide-react'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'
import './Services.css'

// Who a service is mainly for (CMS Service.audience). Visitors filter the catalogue by it.
const AUDIENCES = { startups: 'Startups and MSMEs', researchers: 'Researchers and academic groups', industry: 'Industry', health: 'Health workers and providers' }
const lines = (t) => String(t || '').split('\n').map((l) => l.replace(/^[-•*]\s*/, '').trim()).filter(Boolean)

// What a visitor does next for each kind of service; the CMS button text and link win when they are set.
const ACTIONS = [
  [/prototyp|testing|facilit/i, 'Request facility access', '/facilities/#use-a-facility'],
  [/r\s*&?\s*d|research/i, 'Discuss a prototype', '/contact/'],
  [/regulat|certif/i, 'Ask about regulatory guidance', '/contact/'],
  [/train|capacity/i, 'Ask about training', '/contact/'],
  [/market|scal|sustain/i, 'Explore collaboration', '/contact/'],
]
const actionFor = (item) => {
  const [, label, to] = ACTIONS.find(([re]) => re.test(item.title || '')) || [null, 'Ask about this', '/contact/']
  return { label: item.cta_label || label, to: item.cta_link || to }
}

function Service({ item }) {
  const offer = lines(item.includes)
  const act = actionFor(item)
  return (
    <li className="sv" id={`service-${item.id}`}>
      <div className="sv__head">
        <div>
          <h3 className="sv__title">{(item.title || '').replace('R & D', 'R&D')}</h3>
          {AUDIENCES[item.audience] && <p className="sv__for">For {AUDIENCES[item.audience].toLowerCase()}</p>}
        </div>
      </div>
      {(item.description || offer.length > 0 || item.how_to_access) && (
        <div className="sv__body">
          {item.description && <p className="sv__desc">{item.description}</p>}
          {offer.length > 0 && (
            <ul className="sv__offer" aria-label="What is offered">
              {offer.map((o) => <li key={o}>{o}</li>)}
            </ul>
          )}
          {item.how_to_access && <p className="sv__how"><strong>How to get it.</strong> {item.how_to_access}</p>}
        </div>
      )}
      <a className="sv__cta" href={act.to}>
        {act.label}<span className="visually-hidden">: {(item.title || '').replace('R & D', 'R&D')}</span> <ArrowRight size={16} aria-hidden="true" />
      </a>
    </li>
  )
}

/* The catalogue: one row per service; a filter by audience appears once services carry one. */
function Catalogue({ items }) {
  const present = useMemo(() => Object.keys(AUDIENCES).filter((a) => items.some((i) => i.audience === a)), [items])
  const [who, setWho] = useState('')
  const shown = who ? items.filter((i) => i.audience === who) : items
  return (
    <>
      {present.length > 1 && (
        <div className="sv-filter" role="group" aria-label="Show services for">
          <button type="button" aria-pressed={!who} onClick={() => setWho('')}>All services</button>
          {present.map((a) => (
            <button type="button" key={a} aria-pressed={who === a} onClick={() => setWho(a)}>{AUDIENCES[a]}</button>
          ))}
        </div>
      )}
      <ul className="sv-list">
        {shown.map((i) => <Service item={i} key={i.id} />)}
      </ul>
    </>
  )
}

/* How CRTDH works with an MSME: the stages and tasks from the CMS objectives table (also on the About page). */
function Process({ rows }) {
  const stages = []
  for (const r of rows || []) {
    if (!r.category) continue
    let st = stages.find((x) => x.name === r.category)
    if (!st) stages.push((st = { name: r.category, tasks: [] }))
    if (r.task && !st.tasks.includes(r.task)) st.tasks.push(r.task)
  }
  if (stages.length < 3) return null
  return (
    <section className="sv-process" aria-labelledby="sv-process-title">
      <div className="container sv-process__grid">
        <div className="sv-process__head">
          <h2 className="section-title" id="sv-process-title">How CRTDH works with an MSME</h2>
          <p>From an idea to the first sales, in the order CRTDH supports it.</p>
          <a className="sv__cta" href="/about/#objectives">See the full table on the About page <ArrowRight size={16} aria-hidden="true" /></a>
        </div>
        <ol className="sv-process__list">
          {stages.map((st) => (
            <li key={st.name}>
              <h3>{st.name}</h3>
              <ul>{st.tasks.map((t) => <li key={t}>{t}</li>)}</ul>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

function ServicesView() {
  const { data: services, loading, error } = useApi(() => fetchList('/services/'), [], [])
  const { data: rows } = useApi(() => fetchList('/objective-rows/'), [], [])

  return (
    <div>
      <PageHero
        page="services"
        eyebrow="Services"
        title="What CRTDH offers"
        description="Testing, prototyping, certification support and technology transfer services for healthcare innovators."
      />

      <section data-block="services.list" className="section">
        <div className="container">
          <Reveal className="section-head">
            <h2 className="section-title">Find the support you need</h2>
          </Reveal>
          <DataState loading={loading} error={error} data={services} emptyProps={{ title: 'Services list coming soon' }}>
            {(items) => <Catalogue items={items} />}
          </DataState>
        </div>
      </section>

      <Process rows={rows} />

      <section className="svc-cta">
        <div className="container svc-cta__row">
          <div>
            <h2 className="svc-cta__title">Not sure which service you need?</h2>
            <p>Tell us about your device, test or idea and we will point you to the right people.</p>
          </div>
          <a className="btn btn--primary" href="/contact/">Send an enquiry</a>
        </div>
      </section>
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Services({ data }) {
  return (
    <PageDataProvider data={data}>
      <ServicesView />
    </PageDataProvider>
  )
}
