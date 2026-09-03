import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import ImageGrid from '../components/ImageGrid'
import ImageGridBlockSection from '../components/ImageGridBlockSection'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'

export default function Facilities() {
  const { data: equipment, loading, error } = useApi(() => fetchList('/equipment/'), [], [])
  const { data: blocks, loading: blocksLoading, error: blocksError } = useApi(
    () => fetchList('/image-grid-blocks/', { params: { page: 'facilities' } }),
    [],
    [],
  )
  const facilityBlocks = (blocks || []).filter((b) => !b.page || b.page === 'facilities')

  return (
    <div>
      <PageHero
        eyebrow="Facilities"
        title="Equipment &amp; manufacturing infrastructure"
        description="Instrumentation, pilot manufacturing and sterile facilities available to CRTDH researchers and partner enterprises."
      />

      <section className="section">
        <div className="container">
          <Reveal className="section-head">
            <span className="eyebrow">Equipment</span>
            <h2 className="section-title">Lab &amp; testing equipment</h2>
          </Reveal>
          <DataState loading={loading} error={error} data={equipment} emptyProps={{ title: 'Equipment list coming soon' }}>
            {(items) => <ImageGrid items={items} labelKey="name" />}
          </DataState>
        </div>
      </section>

      <section className="section section--alt">
        <div className="container">
          <Reveal className="section-head">
            <span className="eyebrow">Manufacturing</span>
            <h2 className="section-title">Pilot plant &amp; manufacturing units</h2>
          </Reveal>
          <DataState
            loading={blocksLoading}
            error={blocksError}
            data={facilityBlocks}
            emptyProps={{ title: 'Facility gallery coming soon' }}
          >
            {(items) => items.map((block) => <ImageGridBlockSection block={block} key={block.id} columns={3} />)}
          </DataState>
        </div>
      </section>
    </div>
  )
}
