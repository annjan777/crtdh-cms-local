import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import Carousel from '../components/Carousel'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'
import './Innovations.css'

export default function Innovations() {
  const { data: innovations, loading, error } = useApi(() => fetchList('/innovations/'), [], [])
  const { data: projectSlides, loading: slidesLoading } = useApi(
    () => fetchList('/project-slides/'),
    [],
    [],
  )

  return (
    <div>
      <PageHero
        eyebrow="Innovations"
        title="Devices &amp; diagnostics from the lab bench to the clinic"
        description="CRTDH-developed medical devices, diagnostics and digital health tools, built for low-resource settings."
      />

      {!slidesLoading && projectSlides && projectSlides.length > 0 && (
        <section className="section section--tight section--alt">
          <div className="container">
            <Reveal className="section-head">
              <span className="eyebrow">Highlights</span>
              <h2 className="section-title">Project spotlight</h2>
            </Reveal>
            <Carousel
              items={projectSlides}
              ariaLabel="Project highlight carousel"
              renderItem={(slide) => (
                <div className="project-slide">
                  <img src={slide.image} alt={slide.title || ''} />
                  {slide.title && <div className="project-slide__caption">{slide.title}</div>}
                </div>
              )}
            />
          </div>
        </section>
      )}

      <section className="section">
        <div className="container">
          <DataState
            loading={loading}
            error={error}
            data={innovations}
            emptyProps={{ title: 'Innovations coming soon', message: 'Check back for device and diagnostic write-ups.' }}
          >
            {(items) => (
              <div className="innovation-list">
                {items.map((innovation, i) => (
                  <Reveal as="article" className="innovation card" key={innovation.id} delay={Math.min(i, 4) * 0.06}>
                    {innovation.images && innovation.images.length > 0 && (
                      <div className="innovation__gallery">
                        {innovation.images.slice(0, 4).map((img) => (
                          <figure key={img.id}>
                            <img src={img.image} alt={img.caption || innovation.title} loading="lazy" />
                          </figure>
                        ))}
                      </div>
                    )}
                    <div className="innovation__content">
                      <h2>{innovation.title}</h2>
                      {innovation.body && (
                        <div
                          className="rich-text"
                          // Backend sanitizes this HTML with bleach before storage.
                          dangerouslySetInnerHTML={{ __html: innovation.body }}
                        />
                      )}
                      {innovation.video_url && (
                        <div className="innovation__video">
                          <iframe
                            src={toYouTubeEmbed(innovation.video_url)}
                            title={innovation.title}
                            allow="accelerometer; autoplay; encrypted-media; picture-in-picture"
                            allowFullScreen
                          />
                        </div>
                      )}
                    </div>
                  </Reveal>
                ))}
              </div>
            )}
          </DataState>
        </div>
      </section>
    </div>
  )
}

function toYouTubeEmbed(url) {
  try {
    const u = new URL(url)
    if (u.hostname.includes('youtu.be')) return `https://www.youtube.com/embed/${u.pathname.slice(1)}`
    const id = u.searchParams.get('v')
    return id ? `https://www.youtube.com/embed/${id}` : url
  } catch {
    return url
  }
}
