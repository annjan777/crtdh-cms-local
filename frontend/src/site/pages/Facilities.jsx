import { useRef, useState } from 'react'
import { ArrowUpRight } from 'lucide-react'
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
      <div className="fac-plants__head">
        {block.section_title && <h3 className="fac-plants__title">{block.section_title}</h3>}
        {block.intro && <p className="fac-plants__intro">{block.intro}</p>}
      </div>
      <PhotoMosaic items={block.items} label={block.section_title} />
    </div>
  )
}

// Equipment grouped by what it lets a user do. The CMS has no category for equipment, so the group comes from
// the instrument's name; anything that matches no group is listed under "Other equipment", never dropped.
const GROUPS = [
  { id: 'sterile', title: 'Sterile work, storage and fluid handling', match: /sterile|bsl|cryogenic|refrigerat|autoclave|heat chamber|dispenser|syringe/i },
  { id: 'prototyping', title: 'Prototyping and fabrication', match: /pcb|solder|laser|3d print/i },
  { id: 'testing', title: 'Testing, imaging and computing', match: /amplifier|waveform|power supply|multimeter|spectrum|thermal imaging|ecg|server|computer/i },
  { id: 'manufacturing', title: 'Pilot manufacturing and packaging', match: /manufactur|pilot plant|plant|packag|kit prep/i },
  { id: 'clinical', title: 'Clinical and field', match: /pathology|clinic|lab at/i },
]
function groupEquipment(items) {
  const groups = GROUPS.map((g) => ({ ...g, items: [] }))
  const other = { id: 'other', title: 'Other equipment', items: [] }
  for (const e of items) (groups.find((g) => g.match.test(e.name || '')) || other).items.push(e)
  return [...groups, other].filter((g) => g.items.length)
}

// Each group: instruments with a photo as tiles (same square frame, photo shown whole), those without a photo
// listed by name under them, so there is never a placeholder tile. One lightbox steps through every photo.
function Equipment({ items }) {
  const groups = groupEquipment(items)
  const photos = groups.flatMap((g) => g.items.filter((e) => e.image))
  const [open, box] = useLightbox(photos.map((e) => ({ ...e, caption: e.name })))
  return (
    <>
      {groups.map((g) => {
        const withPhoto = g.items.filter((e) => e.image)
        const noPhoto = g.items.filter((e) => !e.image)
        return (
          <div className="fac-group" key={g.id} aria-labelledby={`fac-group-${g.id}`} role="group">
            <h3 className="fac-group__title" id={`fac-group-${g.id}`}>{g.title}</h3>
            {withPhoto.length > 0 && (
              <ul className="fac-equip">
                {withPhoto.map((e) => (
                  <li key={e.id}>
                    <button type="button" className="fac-equip__item" onClick={() => open(photos.indexOf(e))}>
                      <span className="fac-equip__img"><img src={e.image} alt="" loading="lazy" /></span>
                      <span className="fac-equip__name">{e.name}</span>
                      <span className="visually-hidden">: open a larger photo</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {noPhoto.length > 0 && (
              <ul className="fac-also__list" aria-label={`${g.title}: more equipment`}>
                {noPhoto.map((e) => <li key={e.id}>{e.name}</li>)}
              </ul>
            )}
          </div>
        )
      })}
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
  const { data: documents } = useApi(() => fetchList('/documents/'), [], [])
  const membershipPdf = (documents || []).find((d) => d.category === 'membership' && d.file)?.file
  const ref = useRef(null)
  usePageMotion(ref, [equipment, blocks])

  return (
    <div ref={ref}>
      <PageHero
        page="facilities"
        eyebrow="Facilities"
        title="Our facilities"
        description="Instrumentation, pilot manufacturing and sterile facilities available to CRTDH researchers and partner enterprises."
        image={firstBlockImage(facilityBlocks)}
      />

      <nav className="fac-nav" aria-label="On this page">
        <div className="container fac-nav__row">
          <a href="#manufacturing-plants">Manufacturing units</a>
          <a href="#equipment">Lab &amp; testing equipment</a>
          <a href="#use-a-facility">Who can use them</a>
        </div>
      </nav>

      <section data-block="facilities.photo-sections" id="manufacturing-plants" className="fac-sec">
        <div className="container">
          <div className="fac-sec__head">
            <h2 className="section-title">Pilot plant &amp; manufacturing units</h2>
          </div>
          <DataState loading={blocksLoading} error={blocksError} data={facilityBlocks} emptyProps={{ title: 'Facility gallery coming soon' }}>
            {(items) => items.map((block) => <PlantBlock block={block} key={block.id} />)}
          </DataState>
        </div>
      </section>

      <section data-block="facilities.equipment" id="equipment" className="fac-sec fac-sec--alt">
        <div className="container">
          <div className="fac-sec__head fac-sec__head--split">
            <div>
              <h2 className="section-title">Lab &amp; testing equipment</h2>
            </div>
            <p>Select a photo to see it larger.</p>
          </div>
          <DataState loading={loading} error={error} data={equipment} emptyProps={{ title: 'Equipment list coming soon' }}>
            {(items) => <Equipment items={items} />}
          </DataState>
        </div>
      </section>

      {/* Who can use the facilities and how: from the CRTDH membership details (PDF). */}
      <section className="fac-cta" id="use-a-facility">
        <div className="container fac-cta__row">
          <div className="fac-cta__copy">
            <h2 className="fac-cta__title">Use a facility</h2>
            <p>
              MSMEs and startups can book CRTDH equipment and pilot plants by the hour through the annual membership
              (Platinum, Gold or Silver). Slots depend on availability, and rates do not include consumables or consultancy.
            </p>
            {membershipPdf && (
              <a className="fac-cta__doc" href={membershipPdf} target="_blank" rel="noreferrer">Membership tiers and hourly rates (PDF)</a>
            )}
          </div>
          <a className="btn btn--primary" href="/contact/">Ask about a booking <ArrowUpRight size={18} aria-hidden="true" /></a>
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
