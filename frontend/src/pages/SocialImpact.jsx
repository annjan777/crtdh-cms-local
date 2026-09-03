import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import ImageGridBlockSection from '../components/ImageGridBlockSection'
import VideoBlock from '../components/VideoBlock'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'

export default function SocialImpact() {
  const { data: blocks, loading, error } = useApi(
    () => fetchList('/image-grid-blocks/', { params: { page: 'social-impact' } }),
    [],
    [],
  )
  const { data: videos, loading: videoLoading } = useApi(
    () => fetchList('/video-blocks/', { params: { page: 'social-impact' } }),
    [],
    [],
  )
  const impactBlocks = (blocks || []).filter((b) => !b.page || b.page === 'social-impact')
  const impactVideos = (videos || []).filter((v) => !v.page || v.page === 'social-impact')

  return (
    <div>
      <PageHero
        eyebrow="Social Impact"
        title="Technology reaching communities"
        description="Health camps, rural clinics and outreach programmes bringing CRTDH innovations to the people who need them most."
      />

      <section className="section">
        <div className="container">
          <DataState
            loading={loading}
            error={error}
            data={impactBlocks}
            emptyProps={{ title: 'Outreach gallery coming soon' }}
          >
            {(items) => items.map((block) => <ImageGridBlockSection block={block} key={block.id} columns={4} />)}
          </DataState>
        </div>
      </section>

      {!videoLoading && impactVideos.length > 0 && (
        <section className="section section--alt">
          <div className="container">
            <Reveal className="section-head">
              <span className="eyebrow">Stories</span>
              <h2 className="section-title">Community stories</h2>
            </Reveal>
            <div className="grid grid--2">
              {impactVideos.map((block) => (
                <VideoBlock block={block} key={block.id} />
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
