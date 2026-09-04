import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import ImageGridBlockSection from '../components/ImageGridBlockSection'
import VideoBlock from '../components/VideoBlock'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'

import Carousel from '../components/Carousel'

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
  const impactBlocks = (blocks || [])
    .filter((b) => !b.page || b.page === 'social-impact')
    .filter((block, index, self) => self.findIndex(t => t.section_title === block.section_title) === index)
  
  const impactVideos = (videos || [])
    .filter((v) => !v.page || v.page === 'social-impact')
    .filter((video, index, self) => self.findIndex(t => t.title === video.title) === index)

  return (
    <div>
      <PageHero
        eyebrow="Social Impact"
        title="Technology reaching communities"
        description="Health camps, rural clinics and outreach programmes bringing CRTDH innovations to the people who need them most."
      />

      <section className="section" style={{ paddingBottom: '0' }}>
        <div className="container" style={{ maxWidth: '900px', margin: '0 auto', fontSize: '1.05rem', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
          <p style={{ marginBottom: '1.5rem' }}>
            The CRTDH & its implementation partner, FIH, has pioneered clusters of technology-enabled e-health clinics in remote villages where even primary healthcare centers do not function. This has fostered a silent socio-economic revolution where certified community health-workers deliver healthcare-support to last-mile populations. Large numbers of rural women have been trained to work as an interface between the patient, 'remote' doctor and the invented frugal diagnostic-technologies, enabling the establishment of their self-esteem and sustainable livelihood in the process. Empowered by a 'primary-care software', this has led to an all-in-one real-time data-driven clinical decision support system allowing for screening and risk-assessment of patients vetted by remote doctors to ensure high-quality evidence-based tailor-made advice. These centres make genuine medicines available to the rural population (where spurious medicines are sold in an unchecked manner), deliver basic physiotherapy services, undertake school & community-based health education and awareness activities; including manufacturing of simple health products such as Sanitizer, Face mask, Oral Rehydration Salts, Sanitary Napkins etc.
          </p>
          <p>
            The various initiatives under CRTDH have thus promised to create variety of new jobs and self-employment opportunities locally, thereby reducing the need for mass migration of population to centralized hotspots for machinery manufacturing, consumables and pharmaceutics, software, information systems and analytics etc. Reduction in job associated migrant population would also allow for local and regional developments when people tend to stay longer in their place of bringing up, arresting the need for mitigating migrant population movement during times of crisis. Further, this will generate local small scale enterprises, strengthening a distributed local ecosystem of micro, small and medium enterprises for serving healthcare needs, thereby strengthening self-reliant local economic growth. This will further stimulate localized economy of small scale jobs across spectrum of skills, fostering locally sustained economy, minimizing the variance in spectrum of regional per capita income across the country.
          </p>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <DataState
            loading={loading}
            error={error}
            data={impactBlocks}
            emptyProps={{ title: 'Outreach gallery coming soon' }}
          >
            {(items) => items.map((block) => {
              const uniqueItems = block.items.filter((item, i, self) => self.findIndex(t => t.image === item.image && t.caption === item.caption) === i)
              return (
                <div className="image-grid-block" id={block.anchor_slug || undefined} key={block.id} style={{ marginBottom: 'var(--space-8)' }}>
                  <Carousel
                    items={uniqueItems}
                    ariaLabel={block.section_title || 'Image carousel'}
                    renderItem={(item) => (
                      <div className="project-slide project-slide--auto">
                        <img src={item.image} alt={item.caption || ''} style={{ objectFit: 'contain', width: '100%', height: 'auto', maxHeight: '500px', display: 'block', margin: '0 auto' }} />
                        {item.caption && <div className="project-slide__caption">{item.caption}</div>}
                      </div>
                    )}
                  />
                </div>
              )
            })}
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

      <section className="section">
        <div className="container">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 'var(--space-8)' }}>
            <video width="100%" controls style={{ borderRadius: 'var(--radius-md)', background: '#000', boxShadow: 'var(--shadow-sm)', aspectRatio: '16/9' }}>
              <source src="/videos/jsv-video.mp4" type="video/mp4" />
              Your browser does not support HTML video.
            </video>
            <video width="100%" controls style={{ borderRadius: 'var(--radius-md)', background: '#000', boxShadow: 'var(--shadow-sm)', aspectRatio: '16/9' }}>
              <source src="/videos/Community-engagement.mp4" type="video/mp4" />
              Your browser does not support HTML video.
            </video>
          </div>
        </div>
      </section>
    </div>
  )
}
