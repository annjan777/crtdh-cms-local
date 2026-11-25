import { useRef } from 'react'
import { ArrowRight, ArrowUpRight } from 'lucide-react'
import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList, fetchOne } from '../api/client'
import PageHero, { firstBlockImage } from '../components/PageHero'
import PhotoMosaic from '../components/PhotoMosaic'
import VideoBlock from '../components/VideoBlock'
import { DataState } from '../components/StateBlock'
import { usePageMotion } from '../components/motion4.js'
import './Enterprises.css'

function EnterprisesView() {
  const { data: enterprises, loading, error } = useApi(() => fetchList('/enterprises/'), [], [])
  const { data: home } = useApi(() => fetchOne('/home-page/'), [], null)
  const { data: blocks, loading: blocksLoading } = useApi(
    () => fetchList('/image-grid-blocks/', { params: { page: 'enterprises' } }),
    [],
    [],
  )
  const { data: videoBlocks, loading: videoLoading } = useApi(
    () => fetchList('/video-blocks/', { params: { page: 'enterprises' } }),
    [],
    [],
  )
  const enterpriseBlocks = (blocks || []).filter((b) => !b.page || b.page === 'enterprises')
  const enterpriseVideos = (videoBlocks || []).filter((v) => !v.page || v.page === 'enterprises')
  const ref = useRef(null)
  usePageMotion(ref, [enterprises, blocks, home])

  // Ways in for an enterprise: each goes to a real page or the CMS membership document.
  const entries = [
    { title: 'Use our facilities', text: 'Sterile rooms, pilot plants and test equipment.', href: '/facilities/' },
    { title: 'License a technology', text: 'Devices and diagnostics developed at CRTDH.', href: '/innovations/' },
    { title: 'Get support', text: 'R&D, prototyping, regulatory and market access.', href: '/services/' },
    home?.membership_pdf && { title: home.membership_heading || 'Annual membership', text: 'Membership details for MSMEs and startups (PDF).', href: home.membership_pdf, external: true },
  ].filter(Boolean)

  return (
    <div ref={ref}>
      <PageHero
        page="enterprises"
        eyebrow="Industry & MSMEs"
        title="Collaborate with CRTDH"
        description="The enterprise cluster CRTDH supports — from women-led rural livelihood ventures to medtech startups scaling manufacturing."
        image={firstBlockImage(enterpriseBlocks, 1)}
      />

      <nav className="ent-entries" aria-label="Ways to work with CRTDH">
        <ul className="container ent-entries__row">
          {entries.map(({ title, text, href, external }, k) => (
            <li key={title} style={{ '--d': `${k * 80}ms` }}>
              <a className="ent-entry" href={href} {...(external ? { target: '_blank', rel: 'noreferrer' } : {})}>
                <span className="ent-entry__body">
                  <span className="ent-entry__title">{title}</span>
                  <span className="ent-entry__text">{text}</span>
                </span>
                {external ? <ArrowUpRight className="ent-entry__go" size={18} aria-hidden="true" /> : <ArrowRight className="ent-entry__go" size={18} aria-hidden="true" />}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {home?.enterprises_text && (
        <section className="ent-why">
          <div className="container ent-why__grid">
            <div>
              <h2 className="section-title">Manufacturing healthcare technology in India</h2>
              <p className="ent-why__text">{home.enterprises_text}</p>
            </div>
            {home.msme_map_image && (
              <figure className="ent-why__map" data-rv="mask">
                <img src={home.msme_map_image} alt={home.msme_caption || 'MSME cluster map'} loading="lazy" />
                {home.msme_caption && <figcaption>{home.msme_caption}</figcaption>}
              </figure>
            )}
          </div>
        </section>
      )}

      <section data-block="enterprises.list" className="ent-wall">
        <div className="container">
          <div className="ent-wall__head">
            <h2 className="section-title">Enterprises we work with</h2>
          </div>
          <DataState loading={loading} error={error} data={enterprises} emptyProps={{ title: 'Enterprise directory coming soon' }}>
            {(items) => (
              <ul className="ent-wall__grid">
                {items.map((ent, k) => (
                  <li className="ent-logo" key={ent.id} data-rv="fade" style={{ '--d': `${(k % 6) * 50}ms` }}>
                    <span className="ent-logo__mark">
                      {ent.logo ? <img src={ent.logo} alt="" loading="lazy" /> : <span className="ent-logo__initials" aria-hidden="true">{ent.name.replace(/^M\/s\s+/i, '').split(/\s+/).slice(0, 2).map((w) => w[0]).join('')}</span>}
                    </span>
                    <span className="ent-logo__name">{ent.name}</span>
                    {ent.subtitle && <span className="ent-logo__sub">{ent.subtitle}</span>}
                  </li>
                ))}
              </ul>
            )}
          </DataState>
        </div>
      </section>

      {!blocksLoading && enterpriseBlocks.length > 0 && (
        <section data-block="enterprises.photo-sections" className="ent-photos">
          <div className="container">
            {enterpriseBlocks.map((block) => (
              <div className="ent-photos__block" id={block.anchor_slug || undefined} key={block.id}>
                <div className="ent-photos__head">
                  {block.section_title && <h2 className="section-title">{block.section_title}</h2>}
                  {block.intro && <p>{block.intro}</p>}
                </div>
                <PhotoMosaic items={block.items} label={block.section_title} />
              </div>
            ))}
          </div>
        </section>
      )}

      {!videoLoading && enterpriseVideos.length > 0 && (
        <section data-block="enterprises.videos" className="section">
          <div className="container">
            <div className="section-head">
              <h2 className="section-title">Enterprise stories</h2>
            </div>
            <div className="grid grid--2">
              {enterpriseVideos.map((block) => <VideoBlock block={block} key={block.id} />)}
            </div>
          </div>
        </section>
      )}

      <section className="ent-cta">
        <div className="container ent-cta__row">
          <h2 className="ent-cta__title">Bring us your device, process or idea.</h2>
          <a className="btn btn--primary" href="/contact/">Start a conversation <ArrowUpRight size={18} aria-hidden="true" /></a>
        </div>
      </section>
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Enterprises({ data }) {
  return (
    <PageDataProvider data={data}>
      <EnterprisesView />
    </PageDataProvider>
  )
}
