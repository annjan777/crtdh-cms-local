import { useRef } from 'react'
import { PageDataProvider } from '../api/data.jsx'
import { usePageMotion } from '../components/motion4.js'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero, { firstBlockImage } from '../components/PageHero'
import VideoBlock from '../components/VideoBlock'
import { DataState } from '../components/StateBlock'
import './SocialImpact.css'

import PhotoMosaic from '../components/PhotoMosaic'

function Covid19View() {
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

  const ref = useRef(null)
  usePageMotion(ref, [blocks, videos])

  return (
    <div ref={ref}>
      <PageHero
        page="covid-19"
        eyebrow="Archive · Covid-19 response"
        title="CRTDH's response to the pandemic"
        description="Diagnostics, PPE and community relief efforts undertaken by CRTDH during the Covid-19 pandemic."
        image={firstBlockImage(covidBlocks)}
      />

      <section data-block="covid-19.story" className="section">
        <div className="container story" data-rv>
          <p className="cv-archive" role="note">
            <strong>Archive.</strong> This page records CRTDH&apos;s work during the Covid-19 pandemic, from 2020. The
            products and services it describes may no longer be offered; for current technologies, see{' '}
            <a href="/innovations/">Innovations</a>.
          </p>
          <span className="eyebrow">Covid-19</span>
          <h2>Turning a crisis into an opportunity</h2>
          <p>
            In 2020, Covid-19 turned the world upside down. The CRTDH research group set out to turn the crisis into an
            opportunity: a diagnostic device that could run nucleic-acid tests outside a structured laboratory. The team
            developed a piece-wise isothermal nucleic acid test (PINAT), a platform technology for diagnosing
            pathogen-associated infections, including but not limited to Covid-19. PINAT was designed to give the
            accuracy of a molecular test at a very low cost, with the simplicity of a common rapid test.
          </p>
          <p>
            The pandemic showed how scarce accurate, low-cost and easy-to-use diagnostics were, and how hard they were to
            manufacture at scale. Simple, reasonably sensitive tests for community-level testing can catch early and
            asymptomatic infections and reduce community transmission. CRTDH&apos;s technology work therefore focused on
            diagnostics that combine the standards of laboratory tests with the convenience of rapid tests, so that
            people with the least access to healthcare get the same quality of testing. By engaging women as frontline
            health workers, the work also aimed to create rural employment and livelihoods.
          </p>
          <p>
            The effort also involved micro, small and medium enterprises in manufacturing these products, which opened
            new employment opportunities during a difficult period.
          </p>
        </div>
      </section>

      <section data-block="covid-19.photo-sections" className="cv-photos">
        <div className="container">
          <DataState loading={loading} error={error} data={covidBlocks} emptyProps={{ title: 'Response gallery coming soon' }}>
            {(items) => items.map((block) => (
              <div className="cv-photos__block" id={block.anchor_slug || undefined} key={block.id}>
                <div className="cv-photos__head" data-rv>
                  <span className="eyebrow">In pictures</span>
                  {block.section_title && <h2 className="section-title">{block.section_title}</h2>}
                  {block.intro && <p>{block.intro}</p>}
                </div>
                <PhotoMosaic items={block.items} label={block.section_title} />
              </div>
            ))}
          </DataState>
        </div>
      </section>

      {!videoLoading && covidVideos.length > 0 && (
        <section data-block="covid-19.videos" className="ri-videos">
          <div className="container">
            <div className="ri-videos__head" data-rv>
              <span className="eyebrow eyebrow--on-dark">Coverage</span>
              <h2 className="ri-videos__title">Response in action</h2>
            </div>
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

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Covid19({ data }) {
  return (
    <PageDataProvider data={data}>
      <Covid19View />
    </PageDataProvider>
  )
}
