import { Factory } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import ImageGridBlockSection from '../components/ImageGridBlockSection'
import VideoBlock from '../components/VideoBlock'
import { DataState } from '../components/StateBlock'
import Reveal, { Stagger, StaggerItem } from '../components/Reveal'
import './Enterprises.css'

export default function Enterprises() {
  const { data: enterprises, loading, error } = useApi(() => fetchList('/enterprises/'), [], [])
  const { data: blocks, loading: blocksLoading } = useApi(
    () => fetchList('/image-grid-blocks/', { params: { page: 'enterprises' } }),
    [],
    [],
  )
  const { data: videoBlocks, loading: videoLoading } = useApi(
    () => fetchList('/video-blocks/', { params: { page: 'enterprises' } }),
    [],
    [],
  )
  const enterpriseBlocks = (blocks || []).filter((b) => !b.page || b.page === 'enterprises')
  const enterpriseVideos = (videoBlocks || []).filter((v) => !v.page || v.page === 'enterprises')

  return (
    <div>
      <PageHero
        eyebrow="Enterprises"
        title="MSMEs &amp; startups engaged with CRTDH"
        description="The enterprise cluster CRTDH supports — from women-led rural livelihood ventures to medtech startups scaling manufacturing."
      />

      <section className="section">
        <div className="container">
          <Reveal className="section-head">
            <span className="eyebrow">Cluster</span>
            <h2 className="section-title">Enterprises engagement</h2>
          </Reveal>
          <DataState loading={loading} error={error} data={enterprises} emptyProps={{ title: 'Enterprise directory coming soon' }}>
            {(items) => (
              <Stagger className="grid grid--4">
                {items.map((ent) => (
                  <StaggerItem key={ent.id}>
                    <div className="card enterprise-card">
                      <div className="enterprise-card__logo">
                        {ent.logo ? <img src={ent.logo} alt={ent.name} loading="lazy" /> : <Factory size={26} aria-hidden="true" />}
                      </div>
                      <p className="enterprise-card__name">{ent.name}</p>
                      {ent.subtitle && <p className="enterprise-card__subtitle">{ent.subtitle}</p>}
                    </div>
                  </StaggerItem>
                ))}
              </Stagger>
            )}
          </DataState>
        </div>
      </section>

      {!blocksLoading && enterpriseBlocks.length > 0 && (
        <section className="section section--alt">
          <div className="container">
            {enterpriseBlocks.map((block) => (
              <ImageGridBlockSection block={block} key={block.id} columns={4} />
            ))}
          </div>
        </section>
      )}

      {!videoLoading && enterpriseVideos.length > 0 && (
        <section className="section">
          <div className="container">
            <Reveal className="section-head">
              <span className="eyebrow">In focus</span>
              <h2 className="section-title">Enterprise stories</h2>
            </Reveal>
            <div className="grid grid--2">
              {enterpriseVideos.map((block) => (
                <VideoBlock block={block} key={block.id} />
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
