import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import ImageGridBlockSection from '../components/ImageGridBlockSection'
import VideoBlock from '../components/VideoBlock'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'

export default function Covid19() {
  const { data: blocks, loading, error } = useApi(
    () => fetchList('/image-grid-blocks/', { params: { page: 'covid-19' } }),
    [],
    [],
  )
  const { data: videos, loading: videoLoading } = useApi(
    () => fetchList('/video-blocks/', { params: { page: 'covid-19' } }),
    [],
    [],
  )
  const covidBlocks = (blocks || []).filter((b) => !b.page || b.page === 'covid-19')
  const covidVideos = (videos || []).filter((v) => !v.page || v.page === 'covid-19')

  return (
    <div>
      <PageHero
        eyebrow="Covid-19 Response"
        title="CRTDH's response to the pandemic"
        description="Diagnostics, PPE and community relief efforts undertaken by CRTDH during the Covid-19 pandemic."
      />

      <section className="section">
        <div className="container">
          <DataState loading={loading} error={error} data={covidBlocks} emptyProps={{ title: 'Response gallery coming soon' }}>
            {(items) => items.map((block) => <ImageGridBlockSection block={block} key={block.id} columns={4} />)}
          </DataState>
        </div>
      </section>

      {!videoLoading && covidVideos.length > 0 && (
        <section className="section section--alt">
          <div className="container">
            <Reveal className="section-head">
              <span className="eyebrow">Coverage</span>
              <h2 className="section-title">Response in action</h2>
            </Reveal>
            <div className="grid grid--2">
              {covidVideos.map((block) => (
                <VideoBlock block={block} key={block.id} />
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
