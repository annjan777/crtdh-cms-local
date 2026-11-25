import { useMemo, useState } from 'react'
import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import { FlaskConical, Wrench, ShieldCheck, GraduationCap, Store, TrendingUp, Sparkles, ArrowRight } from 'lucide-react'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'
import './Services.css'

// Who a service is mainly for (CMS Service.audience). Visitors filter the catalogue by it.
const AUDIENCES = { startups: 'Startups and MSMEs', researchers: 'Researchers and academic groups', industry: 'Industry', health: 'Health workers and providers' }
const lines = (t) => String(t || '').split('\n').map((l) => l.replace(/^[-•*]\s*/, '').trim()).filter(Boolean)

// Icon for a service, from words in its CMS title (the stock illustrations read as dated; the icon is decoration only).
const ICONS = [
  [/r\s*&?\s*d|research/i, FlaskConical],
  [/prototyp|testing/i, Wrench],
  [/regulat|certif|guidance/i, ShieldCheck],
  [/train|capacity|skill/i, GraduationCap],
  [/market|access/i, Store],
  [/scal|sustain/i, TrendingUp],
]
const iconFor = (title) => (ICONS.find(([re]) => re.test(title || '')) || [null, Sparkles])[1]

function Service({ item }) {
  const Icon = iconFor(item.title)
  const offer = lines(item.includes)
  return (
    <li className="sv" id={`service-${item.id}`}>
      <div className="sv__head">
        <span className="sv__icon" aria-hidden="true"><Icon size={26} strokeWidth={1.6} /></span>
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
      <a className="sv__cta" href={item.cta_link || '/contact/'}>
        {item.cta_label || 'Ask about this'}<span className="visually-hidden">: {(item.title || '').replace('R & D', 'R&D')}</span> <ArrowRight size={16} aria-hidden="true" />
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

function ServicesView() {
  const { data: services, loading, error } = useApi(() => fetchList('/services/'), [], [])

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
