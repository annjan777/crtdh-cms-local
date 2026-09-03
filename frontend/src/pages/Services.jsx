import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import ImageGrid from '../components/ImageGrid'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'

export default function Services() {
  const { data: services, loading, error } = useApi(() => fetchList('/services/'), [], [])

  return (
    <div>
      <PageHero
        eyebrow="Services"
        title="What CRTDH offers"
        description="Testing, prototyping, certification support and technology transfer services for healthcare innovators."
      />

      <section className="section">
        <div className="container">
          <Reveal className="section-head">
            <span className="eyebrow">Capabilities</span>
            <h2 className="section-title">Services for healthcare innovators</h2>
          </Reveal>
          <DataState loading={loading} error={error} data={services} emptyProps={{ title: 'Services list coming soon' }}>
            {(items) => <ImageGrid items={items} labelKey="title" columns={3} aspect="wide" />}
          </DataState>
        </div>
      </section>
    </div>
  )
}
