import { useRef, useState } from 'react'
import { ArrowUpRight, Wrench } from 'lucide-react'
import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero, { firstBlockImage } from '../components/PageHero'
import Lightbox from '../components/Lightbox'
import PhotoMosaic from '../components/PhotoMosaic'
import { DataState } from '../components/StateBlock'
import { usePageMotion } from '../components/motion4.js'
import './Facilities.css'

/* One lightbox for a list of {image, caption|name} photos. */
function useLightbox(list) {
  const [at, setAt] = useState(-1)
  const box = at >= 0 && (
    <Lightbox
      images={list}
      currentIndex={at}
      onClose={() => setAt(-1)}
      onNext={() => setAt((i) => (i + 1) % list.length)}
      onPrev={() => setAt((i) => (i - 1 + list.length) % list.length)}
    />
  )
  return [setAt, box]
}

function PlantBlock({ block }) {
  return (
    <div className="fac-plants" id={block.anchor_slug || undefined}>
      <div className="fac-plants__head" data-rv>
        {block.section_title && <h3 className="fac-plants__title">{block.section_title}</h3>}
        {block.intro && <p className="fac-plants__intro">{block.intro}</p>}
      </div>
      <PhotoMosaic items={block.items} label={block.section_title} />
    </div>
  )
}

// Every instrument in CMS order; one without a photo keeps its place as a named tile.
function Equipment({ items }) {
  const withPhoto = items.filter((e) => e.image)
  const [open, box] = useLightbox(withPhoto.map((e) => ({ ...e, caption: e.name })))
  return (
    <>
      <ul className="fac-equip">
        {items.map((e, k) => (
          <li key={e.id} data-rv style={{ '--d': `${(k % 4) * 70}ms` }}>
            {e.image ? (
              <button type="button" className="fac-equip__item" onClick={() => open(withPhoto.indexOf(e))}>
                <span className="fac-equip__img zoom"><img src={e.image} alt="" loading="lazy" /></span>
                <h3 className="fac-equip__name">{e.name}</h3>
                <span className="visually-hidden">Open a larger photo</span>
              </button>
            ) : (
              <div className="fac-equip__item fac-equip__item--text">
                <span className="fac-equip__img fac-equip__img--none" aria-hidden="true"><Wrench size={30} strokeWidth={1.5} /></span>
                <h3 className="fac-equip__name">{e.name}</h3>
              </div>
            )}
          </li>
        ))}
      </ul>
      {box}
    </>
  )
}

function FacilitiesView() {
  const { data: equipment, loading, error } = useApi(() => fetchList('/equipment/'), [], [])
  const { data: blocks, loading: blocksLoading, error: blocksError } = useApi(
    () => fetchList('/image-grid-blocks/', { params: { page: 'facilities' } }),
    [],
    [],
  )
  const facilityBlocks = (blocks || []).filter((b) => !b.page || b.page === 'facilities')
  const ref = useRef(null)
  usePageMotion(ref, [equipment, blocks])

  return (
    <div ref={ref}>
      <PageHero
        eyebrow="Facilities"
        title="Our facilities"
        description="Instrumentation, pilot manufacturing and sterile facilities available to CRTDH researchers and partner enterprises."
        image={firstBlockImage(facilityBlocks)}
      />

      <nav className="fac-nav" aria-label="On this page">
        <div className="container fac-nav__row">
          <a href="#manufacturing-plants">Manufacturing units</a>
          <a href="#equipment">Lab &amp; testing equipment</a>
          <a href="#use-a-facility">Use a facility</a>
        </div>
      </nav>

      <section data-block="facilities.photo-sections" id="manufacturing-plants" className="fac-sec">
        <div className="container">
          <div className="fac-sec__head" data-rv>
            <span className="eyebrow">Manufacturing</span>
            <h2 className="section-title">Pilot plant &amp; manufacturing units</h2>
          </div>
          <DataState loading={blocksLoading} error={blocksError} data={facilityBlocks} emptyProps={{ title: 'Facility gallery coming soon' }}>
            {(items) => items.map((block) => <PlantBlock block={block} key={block.id} />)}
          </DataState>
        </div>
      </section>

      <section data-block="facilities.equipment" id="equipment" className="fac-sec fac-sec--alt">
        <div className="container">
          <div className="fac-sec__head fac-sec__head--split" data-rv>
            <div>
              <span className="eyebrow">Equipment</span>
              <h2 className="section-title">Lab &amp; testing equipment</h2>
            </div>
            <p>Select an instrument to see a larger photo.</p>
          </div>
          <DataState loading={loading} error={error} data={equipment} emptyProps={{ title: 'Equipment list coming soon' }}>
            {(items) => <Equipment items={items} />}
          </DataState>
        </div>
      </section>

      <section className="fac-cta" id="use-a-facility">
        <div className="container fac-cta__row" data-rv>
          <h2 className="fac-cta__title">Want to use a facility or run a test here?</h2>
          <a className="btn btn--primary" href="/contact/">Send an enquiry <ArrowUpRight size={18} aria-hidden="true" /></a>
        </div>
      </section>
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Facilities({ data }) {
  return (
    <PageDataProvider data={data}>
      <FacilitiesView />
    </PageDataProvider>
  )
}
