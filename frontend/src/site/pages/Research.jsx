import { useRef } from 'react'
import { ArrowRight, FlaskConical, Wrench, Rocket } from 'lucide-react'
import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import RichText from '../components/RichText.jsx'
import SiteLink from '../link.jsx'
import { DataState } from '../components/StateBlock'
import { usePageMotion } from '../components/motion4.js'
import './Research.css'

// How the page frames CRTDH's work: the three kinds of work the stories below belong to (design copy, not data).
const MODES = [
  { Icon: FlaskConical, title: 'Discovery', text: 'Fundamental and applied research' },
  { Icon: Wrench, title: 'Development', text: 'Prototyping and engineering' },
  { Icon: Rocket, title: 'Translation', text: 'Validation and real-world use' },
]

/** One research theme as an editorial story: photo on one side, the story on the other. */
export function Story({ s, flip, eyebrow }) {
  return (
    <article className={`rs-story${flip ? ' rs-story--flip' : ''}${s.image ? '' : ' rs-story--text'}`} id={`story-${s.id}`}>
      {s.image && (
        <figure className="rs-story__img zoom" data-rv="mask">
          <img src={s.image} alt={s.image_alt || ''} loading="lazy" />
        </figure>
      )}
      <div className="rs-story__copy" data-rv style={{ '--d': '140ms' }}>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h2 className="rs-story__title">{s.title}</h2>
        {s.summary && <p className="rs-story__summary">{s.summary}</p>}
        {s.body && <RichText html={s.body} className="rich-text" />}
        {s.link_url && <SiteLink to={s.link_url} className="rs-story__link">Read more <ArrowRight size={16} aria-hidden="true" /></SiteLink>}
      </div>
    </article>
  )
}

function ResearchView() {
  const { data: stories, loading, error } = useApi(() => fetchList('/research-stories/', { params: { page: 'research' } }), [], [])
  const list = (stories || []).filter((s) => s.page === 'research')
  const ref = useRef(null)
  usePageMotion(ref, [stories])
  return (
    <div ref={ref}>
      <PageHero
        page="research"
        eyebrow="Research"
        title="Research at CRTDH"
        description="Interdisciplinary research for affordable and deployable healthcare solutions."
        image={list.find((s) => s.image)?.image}
      />
      <nav className="rs-modes" aria-label="Kinds of work">
        <ul className="container rs-modes__row">
          {MODES.map(({ Icon, title, text }, k) => (
            <li key={title} data-rv style={{ '--d': `${k * 100}ms` }}>
              <span className="rs-modes__icon" aria-hidden="true"><Icon size={26} strokeWidth={1.6} /></span>
              <span className="rs-modes__title">{title}</span>
              <span className="rs-modes__text">{text}</span>
            </li>
          ))}
        </ul>
      </nav>
      <section data-block="research.themes" className="rs-list">
        <div className="container">
          <DataState
            loading={loading}
            error={error}
            data={list}
            emptyProps={{ title: 'Research stories are on their way', message: 'Meanwhile, see the technologies they have produced on the Innovations page.' }}
          >
            {(items) => items.map((s, k) => <Story s={s} flip={k % 2 === 1} key={s.id} eyebrow="Research theme" />)}
          </DataState>
        </div>
      </section>
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Research({ data }) {
  return (
    <PageDataProvider data={data}>
      <ResearchView />
    </PageDataProvider>
  )
}
