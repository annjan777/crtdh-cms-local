import { useRef, useState } from 'react'
import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import ImpactFigures from '../components/ImpactFigures'
import PageHero, { firstBlockImage } from '../components/PageHero'
import VideoBlock from '../components/VideoBlock'
import Lightbox from '../components/Lightbox'
import { DataState } from '../components/StateBlock'
import { usePageMotion } from '../components/motion4.js'
import './SocialImpact.css'

// The story told on the previous site (not a CMS field): two paragraphs, each set beside a field photograph.
const STORY = [
  "CRTDH and its implementation partner, FIH, have pioneered clusters of technology-enabled e-health clinics in remote villages where even primary healthcare centres do not function. This has fostered a silent socio-economic revolution where certified community health-workers deliver healthcare-support to last-mile populations. Large numbers of rural women have been trained to work as an interface between the patient, 'remote' doctor and the invented frugal diagnostic-technologies, enabling the establishment of their self-esteem and sustainable livelihood in the process. Empowered by a 'primary-care software', this has led to an all-in-one real-time data-driven clinical decision support system allowing for screening and risk-assessment of patients vetted by remote doctors to ensure high-quality evidence-based tailor-made advice. These centres make genuine medicines available to the rural population (where spurious medicines are sold in an unchecked manner), deliver basic physiotherapy services, undertake school & community-based health education and awareness activities; including manufacturing of simple health products such as sanitiser, face masks, oral rehydration salts and sanitary napkins.",
  'The various initiatives under CRTDH have thus promised to create a variety of new jobs and self-employment opportunities locally, thereby reducing the need for mass migration of population to centralized hotspots for machinery manufacturing, consumables and pharmaceutics, software, information systems and analytics. Reduction in job associated migrant population would also allow for local and regional developments when people tend to stay longer in the places where they grew up, arresting the need for mitigating migrant population movement during times of crisis. Further, this will generate local small-scale enterprises, strengthening a distributed local ecosystem of micro, small and medium enterprises for serving healthcare needs, thereby strengthening self-reliant local economic growth. This will further stimulate localized economy of small-scale jobs across spectrum of skills, fostering locally sustained economy, minimizing the variance in spectrum of regional per capita income across the country.',
]

/* Field photographs as a photo essay: varied sizes, captions under each, opening in a lightbox. */
function PhotoEssay({ block }) {
  const items = (block.items || []).filter((it, i, self) => it.image && self.findIndex((t) => t.image === it.image && t.caption === it.caption) === i)
  const [at, setAt] = useState(-1)
  return (
    <div className="ri-essay" id={block.anchor_slug || undefined}>
      <div className="ri-essay__head" data-rv>
        <span className="eyebrow">In the field</span>
        <h2 className="section-title">{block.section_title || 'Community outreach'}</h2>
        {block.intro && <p>{block.intro}</p>}
      </div>
      <ul className="ri-essay__grid">
        {items.map((it, k) => (
          <li key={it.id ?? k} className={`ri-essay__item ri-essay__item--${['wide', 'tall', 'std', 'std', 'wide', 'std'][k % 6]}`} data-rv={k % 3 === 0 ? 'mask' : undefined} style={{ '--d': `${(k % 3) * 90}ms` }}>
            <button type="button" className="ri-essay__btn" onClick={() => setAt(k)}>
              <span className="ri-essay__img zoom"><img src={it.image} alt={it.caption || ''} loading="lazy" /></span>
              {it.caption && <span className="ri-essay__cap">{it.caption}</span>}
              <span className="visually-hidden">Open photo {k + 1} of {items.length}</span>
            </button>
          </li>
        ))}
      </ul>
      {at >= 0 && (
        <Lightbox
          images={items}
          currentIndex={at}
          onClose={() => setAt(-1)}
          onNext={() => setAt((i) => (i + 1) % items.length)}
          onPrev={() => setAt((i) => (i - 1 + items.length) % items.length)}
        />
      )}
    </div>
  )
}

function SocialImpactView() {
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
    .filter((block, index, self) => self.findIndex((t) => t.section_title === block.section_title) === index)
  const impactVideos = (videos || [])
    .filter((v) => !v.page || v.page === 'social-impact')
    .filter((video, index, self) => self.findIndex((t) => t.title === video.title) === index)
  const ref = useRef(null)
  usePageMotion(ref, [blocks, videos])
  const storyImgs = [firstBlockImage(impactBlocks, 1), firstBlockImage(impactBlocks, 2)]

  return (
    <div ref={ref}>
      <PageHero
        page="social-impact"
        eyebrow="Social Impact"
        title="Impact in rural India"
        description="Health camps, rural clinics and outreach programmes bringing CRTDH innovations to the people who need them most."
        image={firstBlockImage(impactBlocks)}
      />
      <ImpactFigures page="social-impact" />

      <section data-block="social-impact.story" className="ri-story">
        <div className="container">
          {STORY.map((text, k) => (
            <div className={`ri-story__row${k % 2 ? ' ri-story__row--flip' : ''}`} key={k}>
              {storyImgs[k] && (
                <figure className="ri-story__img" data-rv="mask">
                  <img src={storyImgs[k]} alt="" loading="lazy" data-px="0.06" />
                </figure>
              )}
              <p className={`ri-story__text${k === 0 ? ' ri-story__text--lead' : ''}`} data-rv>{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section data-block="social-impact.photo-sections" className="ri-field">
        <div className="container">
          <DataState loading={loading} error={error} data={impactBlocks} emptyProps={{ title: 'Outreach gallery coming soon' }}>
            {(items) => items.map((block) => <PhotoEssay block={block} key={block.id} />)}
          </DataState>
        </div>
      </section>

      {!videoLoading && impactVideos.length > 0 && (
        <section data-block="social-impact.videos" className="ri-videos">
          <div className="container">
            <div className="ri-videos__head" data-rv>
              <span className="eyebrow eyebrow--on-dark">Stories</span>
              <h2 className="ri-videos__title">Community stories</h2>
            </div>
            <div className="grid grid--2">
              {impactVideos.map((block) => <VideoBlock block={block} key={block.id} />)}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function SocialImpact({ data }) {
  return (
    <PageDataProvider data={data}>
      <SocialImpactView />
    </PageDataProvider>
  )
}
