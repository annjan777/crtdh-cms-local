import { useRef, useState } from 'react'
import { BookOpen, HeartHandshake, Home, Stethoscope } from 'lucide-react'
import { fetchOne } from '../api/client'
import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import ImpactFigures from '../components/ImpactFigures'
import PageHero, { firstBlockImage } from '../components/PageHero'
import { usePageData } from '../api/data.jsx'
import VideoBlock from '../components/VideoBlock'
import Lightbox from '../components/Lightbox'
import { DataState } from '../components/StateBlock'
import { usePageMotion } from '../components/motion4.js'
import './SocialImpact.css'

// The rural-health story comes from the CMS (Home page, "Rural healthcare" section: two paragraphs), followed by
// one closing paragraph on local livelihoods that has no CMS field yet.
const CLOSING = "CRTDH's initiatives aim to create local jobs and self-employment, so that fewer people need to leave " +
  'their home regions for work in manufacturing, pharmaceuticals, software or analytics. Small local enterprises in ' +
  'healthcare can strengthen regional economies and support self-reliant growth across a range of skills.'

// What the programme does, as named in the story (no counts: figures come only from the CMS with a source).
const STRANDS = [
  { Icon: Home, title: 'Rural e-health clinics' },
  { Icon: HeartHandshake, title: 'Community health workers' },
  { Icon: Stethoscope, title: 'Screening and remote advice' },
  { Icon: BookOpen, title: 'Health awareness and training' },
]

const HERO_TEXT = 'Health camps, rural clinics and outreach programmes bringing CRTDH innovations to the people who need them most.'

/* Field photographs as a photo essay: varied sizes, captions under each, opening in a lightbox. */
function PhotoEssay({ block, heroText }) {
  const items = (block.items || []).filter((it, i, self) => it.image && self.findIndex((t) => t.image === it.image && t.caption === it.caption) === i)
  const [at, setAt] = useState(-1)
  return (
    <div className="ri-essay" id={block.anchor_slug || undefined}>
      <div className="ri-essay__head">
        <h2 className="section-title">{block.section_title || 'Community outreach'}</h2>
        {/* Skip the intro when it only repeats the page introduction above. */}
        {block.intro && block.intro.trim() !== heroText && <p>{block.intro}</p>}
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
  const { data: home } = useApi(() => fetchOne('/home-page/'), [], null)
  const ref = useRef(null)
  usePageMotion(ref, [blocks, videos, home])
  const story = [home?.women_text_1, home?.women_text_2, CLOSING].filter(Boolean)
  const pageData = usePageData()
  const hero = (pageData?.collections?.['page-heroes'] || []).find((h) => h && h.page === 'social-impact')
  const heroText = (hero?.description || HERO_TEXT).trim()
  const storyImgs = [firstBlockImage(impactBlocks, 1), firstBlockImage(impactBlocks, 2), firstBlockImage(impactBlocks, 3)]

  return (
    <div ref={ref}>
      <PageHero
        page="social-impact"
        eyebrow="Social Impact"
        title="Impact in rural India"
        description={HERO_TEXT}
        image={firstBlockImage(impactBlocks)}
      />
      <ul className="ri-strands" aria-label="What the programme does">
        {STRANDS.map(({ Icon, title }, k) => (
          <li key={title} style={{ '--d': `${k * 80}ms` }}>
            <span className="ri-strands__icon" aria-hidden="true"><Icon size={24} strokeWidth={1.6} /></span>
            <span>{title}</span>
          </li>
        ))}
      </ul>
      <ImpactFigures page="social-impact" />

      <section data-block="social-impact.story" className="ri-story">
        <div className="container">
          {story.map((text, k) => (
            <div className={`ri-story__row${k % 2 ? ' ri-story__row--flip' : ''}`} key={k}>
              {storyImgs[k] && (
                <figure className="ri-story__img" data-rv="mask">
                  <img src={storyImgs[k]} alt="" loading="lazy" data-px="0.06" />
                </figure>
              )}
              <p className={`ri-story__text${k === 0 ? ' ri-story__text--lead' : ''}`}>{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section data-block="social-impact.photo-sections" className="ri-field">
        <div className="container">
          <DataState loading={loading} error={error} data={impactBlocks} emptyProps={{ title: 'Outreach gallery coming soon' }}>
            {(items) => items.map((block) => <PhotoEssay block={block} heroText={heroText} key={block.id} />)}
          </DataState>
        </div>
      </section>

      {!videoLoading && impactVideos.length > 0 && (
        <section data-block="social-impact.videos" className="ri-videos">
          <div className="container">
            <div className="ri-videos__head">
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
