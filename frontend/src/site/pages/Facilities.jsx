import PageShell from '../components/PageShell.jsx'
import { ClosingBand, GridBlock, PageBanner } from '../components/Blocks.jsx'
import { Img } from '../media.jsx'
import { blocksFor } from '../util.js'

/** Facilities (listing): equipment grid, then the manufacturing and demonstration units. */
export default function Facilities({ data }) {
  const c = data.collections || {}
  const equipment = c.equipment || []
  const blocks = blocksFor(c['image-grid-blocks'], 'facilities')
  return (
    <PageShell data={data} className="facilities">
      <PageBanner
        title="Facilities"
        intro="Instrumentation, pilot manufacturing and sterile facilities available to CRTDH researchers and partner enterprises."
      />
      {equipment.length > 0 && (
        <section className="section" aria-labelledby="equipment">
          <div className="wrap">
            <div className="section-head">
              <h2 id="equipment">Laboratory and testing equipment</h2>
            </div>
            <ul className="tiles">
              {equipment.map((e) => (
                <li key={e.id} className="tile card">
                  {e.image ? (
                    <Img src={e.image} alt={e.image_alt || e.name} ratio="3x2" sizes="(min-width: 1024px) 23vw, (min-width: 768px) 30vw, 100vw" />
                  ) : null}
                  <h3 className="tile__title">{e.name}</h3>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
      {blocks.length > 0 && (
        <section className="section section--surface" aria-label="Manufacturing">
          <div className="wrap">
            {blocks.map((b) => (
              // Home links to #manufacturing-plants; the CMS anchor is "manufacturingplants". Keep both working.
              <GridBlock key={b.id} block={b} extraAnchor={b.anchor_slug === 'manufacturingplants' ? 'manufacturing-plants' : undefined} />
            ))}
          </div>
        </section>
      )}
      <ClosingBand
        id="facilities-cta"
        title="Book a facility"
        text="MSMEs, startups and researchers can use the laboratories and pilot plant. Tell us what you want to make or test."
        action="Ask about a facility"
      />
    </PageShell>
  )
}
