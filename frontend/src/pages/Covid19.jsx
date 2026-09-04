import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import ImageGridBlockSection from '../components/ImageGridBlockSection'
import VideoBlock from '../components/VideoBlock'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'

import Carousel from '../components/Carousel'

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
  const covidBlocks = (blocks || [])
    .filter((b) => !b.page || b.page === 'covid-19')
    .filter((block, index, self) => self.findIndex(t => t.section_title === block.section_title) === index)
  
  const covidVideos = (videos || [])
    .filter((v) => !v.page || v.page === 'covid-19')
    .filter((video, index, self) => self.findIndex(t => t.title === video.title) === index)

  return (
    <div>
      <PageHero
        eyebrow="Covid-19 Response"
        title="CRTDH's response to the pandemic"
        description="Diagnostics, PPE and community relief efforts undertaken by CRTDH during the Covid-19 pandemic."
      />

      <section className="section" style={{ paddingBottom: '0' }}>
        <div className="container" style={{ maxWidth: '900px', margin: '0 auto', fontSize: '1.05rem', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
          <h2 style={{ marginBottom: '1.5rem', color: 'var(--color-ink-900)' }}>Combating the <span style={{ color: 'red' }}>Pandemic</span></h2>
          <p style={{ marginBottom: '1.5rem' }}>
            Came the year 2020 - the beginning of a year that would throw the entire world into a tumult, the likes of which this century had not yet seen. Outside the initial, hushed up outbreak in China, talk of a virus was akin to whispered rumours - nothing like the fevered discussion that came to the fore of the public conscious, a few months later. But for the CRTDH research group, this triggered all their endeavours to rise up to the occasion – and they were all working on making a breakthrough, turning the challenge of COVID-19 into an opportunity, by architecting a unique diagnostic device that has attempted to redefine the manner in which nucleic acid best tests may be conducted outside structured laboratory ambience. In response to this challenge, the CRTDH team developed a new piece-wise isothermal nucleic acid test (PINAT) as a platform technology for diagnosing pathogen-associated infections, including but not limited to COVID-19. Disrupting the perception that high-quality molecular diagnostics necessarily demands sophisticated technological and human resources, this diagnostic procedure is the first of its kind, highly accurate ultra-low-cost point-of-care nucleic acid-based test having the simplicity and user-friendliness of a common rapid test.
          </p>

          <p style={{ marginBottom: '1.5rem' }}>
            The ongoing pandemic has exposed the challenges due to scarcity of technology-enabled healthcare solutions that are accurate yet low cost, accessible, user-friendly and amenable to massive manufacturing scale-up and parallelization. The availability of easy-to-use and reasonably sensitive detection methods for community level testing, in such backdrop, for example, holds the potential of capturing the commonly missed cases of early infection and asymptomatic disease presentation and reduce the opportunity for community-level transmission. Such compelling needs, along with other prevailing public health challenges, have paved a clear way forward of the technology wing of the CRTDH towards advancing further on novel diagnostic technologies that essentially offer an amalgamated approach with a trade-off between the scientific standards of high-end laboratory based tests with the elegance of common rapid tests. This paradigm appears to be the future of diagnostics, targeting specific public health measures towards catering the underserved, with no distinction between consumers having expected variabilities in economic barrier, and in the process 'democratize' disease diagnostics by bringing high-end lab tests to the ambit of the bottom of the community pyramid in the green field with no differential treatment of the rich and the poor. Further, by engaging women power as frontline health workers in a sustainable ecosystem and bringing them in the ambit of rural employment generation, the CRTDH has shown a specific approach of establishing gender equality in the underserved community by promoting healthy and economically-supportive livelihood for all.
          </p>
          <p>
            In addition, the empowerment of micro-small-and medium scale enterprises towards participating in manufacturing the most technologically advanced yet deceptively simple medical products have opened up a new paradigm of employment generation under difficult circumstances.
          </p>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <DataState loading={loading} error={error} data={covidBlocks} emptyProps={{ title: 'Response gallery coming soon' }}>
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
