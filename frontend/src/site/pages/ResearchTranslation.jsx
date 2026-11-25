import { useEffect, useRef, useState } from 'react'
import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import { DataState } from '../components/StateBlock'
import { usePageMotion, prefersReducedMotion } from '../components/motion4.js'
import { Story } from './Research.jsx'
import './Research.css'

const STAGES = [
  { id: 'discovery', title: 'Discovery', text: 'A need in the field meets a scientific idea.' },
  { id: 'prototype', title: 'Prototype', text: 'The idea becomes a device that can be tested.' },
  { id: 'validation', title: 'Validation', text: 'The device is tested with samples, clinics and users.' },
  { id: 'translation', title: 'Translation', text: 'Manufacturing, licensing and use in the field.' },
]

/* The four stages as a path; the line draws itself as the reader scrolls through the stories. */
function StagePath({ counts, active }) {
  return (
    <nav className="rt-path" aria-label="Stages">
      <ol className="container rt-path__row">
        {STAGES.map((st, k) => (
          <li key={st.id} className={`rt-stage${counts[st.id] ? '' : ' is-empty'}${k <= active ? ' is-reached' : ''}`}>
            {(() => {
              const inner = (
                <>
                  <span className="rt-stage__dot" aria-hidden="true" />
                  <span className="rt-stage__title">{st.title}</span>
                  <span className="rt-stage__text">{st.text}</span>
                </>
              )
              return counts[st.id] ? <a href={`#stage-${st.id}`}>{inner}</a> : <span className="rt-stage__link">{inner}</span>
            })()}
          </li>
        ))}
      </ol>
    </nav>
  )
}

function TranslationView() {
  const { data: stories, loading, error } = useApi(() => fetchList('/research-stories/', { params: { page: 'research-translation' } }), [], [])
  const list = (stories || []).filter((s) => s.page === 'research-translation')
  const ref = useRef(null)
  usePageMotion(ref, [stories])
  const counts = Object.fromEntries(STAGES.map((st) => [st.id, list.filter((s) => s.stage === st.id).length]))
  const [active, setActive] = useState(prefersReducedMotion() ? 3 : -1)

  useEffect(() => {
    if (prefersReducedMotion() || !('IntersectionObserver' in window)) { setActive(3); return undefined }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) setActive((a) => Math.max(a, Number(e.target.dataset.stageIndex))) })
    }, { rootMargin: '0px 0px -40% 0px' })
    ref.current?.querySelectorAll('[data-stage-index]').forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [stories])

  return (
    <div ref={ref}>
      <PageHero
        page="research-translation"
        eyebrow="Research translation"
        title="From the lab to the field"
        description="The journey from discovery to prototype, validation and translation."
        image={list.find((s) => s.image)?.image}
      />
      <StagePath counts={counts} active={active} />
      <section data-block="research-translation.journey" className="rs-list">
        <div className="container">
          <DataState
            loading={loading}
            error={error}
            data={list}
            emptyProps={{ title: 'The stories behind each stage are on their way', message: 'Meanwhile, see the technologies on the Innovations page.' }}
          >
            {() => STAGES.map((st, k) => {
              const here = list.filter((s) => s.stage === st.id)
              if (!here.length) return null
              return (
                <div className="rt-group" id={`stage-${st.id}`} data-stage-index={k} key={st.id}>
                  <div className="rt-group__head">
                    <span className="rt-group__n" aria-hidden="true">{k + 1}</span>
                    <h2 className="rt-group__title">{st.title}</h2>
                  </div>
                  {here.map((s, i) => <Story s={s} flip={i % 2 === 1} key={s.id} />)}
                </div>
              )
            })}
          </DataState>
        </div>
      </section>
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function ResearchTranslation({ data }) {
  return (
    <PageDataProvider data={data}>
      <TranslationView />
    </PageDataProvider>
  )
}
