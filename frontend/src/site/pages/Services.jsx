import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import { FlaskConical, Wrench, ShieldCheck, GraduationCap, Store, TrendingUp, Sparkles } from 'lucide-react'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'

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

function ServicesView() {
  const { data: services, loading, error } = useApi(() => fetchList('/services/'), [], [])

  return (
    <div>
      <PageHero
        eyebrow="Services"
        title="What CRTDH offers"
        description="Testing, prototyping, certification support and technology transfer services for healthcare innovators."
      />

      <section data-block="services.list" className="section">
        <div className="container">
          <Reveal className="section-head">
            <span className="eyebrow">Capabilities</span>
            <h2 className="section-title">Services for healthcare innovators</h2>
          </Reveal>
          <DataState loading={loading} error={error} data={services} emptyProps={{ title: 'Services list coming soon' }}>
            {(items) => (
              <ul className="svc-list">
                {items.map((i) => {
                  const Icon = iconFor(i.title)
                  return (
                    <li className="svc" key={i.id}>
                      <span className="svc__icon" aria-hidden="true"><Icon size={28} strokeWidth={1.6} /></span>
                      <h3 className="svc__title">{(i.title || '').replace('R & D', 'R&D')}</h3>
                    </li>
                  )
                })}
              </ul>
            )}
          </DataState>
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
