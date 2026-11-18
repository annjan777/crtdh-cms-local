import PageShell from '../components/PageShell.jsx'
import { PageBanner } from '../components/Blocks.jsx'
import { Img } from '../media.jsx'

/** Products (listing): each product with its photographs and commercialisation partners. */
export default function Product({ data }) {
  const products = data.collections?.products || []
  return (
    <PageShell data={data} className="products">
      <PageBanner
        title="Products"
        intro="Products developed and manufactured under CRTDH, with the partners taking them to market."
      />
      {products.length > 0 && (
        <section className="section" aria-label="Products">
          <div className="wrap products__list">
            {products.map((p) => (
              <article key={p.id} className="product" id={`product-${p.id}`}>
                <div className="product__media">
                  {(p.images || []).filter((im) => im.image).slice(0, 3).map((im, i) => (
                    <Img key={im.id} src={im.image} alt={i === 0 ? p.name : ''} ratio="1x1" contain sizes="(min-width: 768px) 22vw, 50vw" />
                  ))}
                </div>
                <div className="product__text">
                  <h2>{p.name}</h2>
                  {(p.partners || []).length > 0 && (
                    <>
                      <h3 className="product__ph">Commercialisation partners</h3>
                      <ul className="partners">
                        {p.partners.map((pt) => (
                          <li key={pt.id}>
                            {pt.logo && <img src={pt.logo} alt="" loading="lazy" height="40" />}
                            <span>{pt.name}</span>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </PageShell>
  )
}
