import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import ImageGrid from '../components/ImageGrid'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'

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
            {(items) => <ImageGrid items={items.map(i => ({ ...i, title: i.title?.replace('R & D', 'R&D') }))} labelKey="title" columns={3} aspect="wide" headingLevel={3} />}
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
