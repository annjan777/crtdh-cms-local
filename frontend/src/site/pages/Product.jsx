import { useRef, useState } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import { DataState } from '../components/StateBlock'
import { usePageMotion } from '../components/motion4.js'
import './Product.css'

const slug = (p) => `product-${p.id}`

/* A product on its own stage: the photo on a light plinth with a photo switcher, the name and its partners. */
function ProductStage({ product, flip }) {
  const imgs = product.images || []
  const [at, setAt] = useState(0)
  return (
    <article className={`pr${flip ? ' pr--flip' : ''}`} id={slug(product)} aria-labelledby={`${slug(product)}-h`}>
      <div className="pr__stage" data-rv="mask">
        {imgs.length > 0 && (
          <div className="pr__photo">
            {imgs.map((im, k) => (
              <img key={im.id} src={im.image} alt={k === at ? product.name : ''} className={k === at ? 'is-current' : ''} loading="lazy" aria-hidden={k !== at} />
            ))}
          </div>
        )}
        {imgs.length > 1 && (
          <div className="pr__dots" role="group" aria-label={`${product.name}: photos`}>
            {imgs.map((im, k) => (
              <button type="button" key={im.id} aria-pressed={k === at} onClick={() => setAt(k)}>
                <img src={im.image} alt={`Photo ${k + 1}`} loading="lazy" />
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="pr__copy" data-rv style={{ '--d': '150ms' }}>
        <span className="eyebrow">Product</span>
        <h2 className="pr__name" id={`${slug(product)}-h`}>{product.name}</h2>
        {product.partners && product.partners.length > 0 && (
          <div className="pr__partners">
            <h3 className="pr__partners-label">Commercialisation partners</h3>
            <ul>
              {product.partners.map((partner) => (
                <li key={partner.id}>
                  <span className="pr__logo">{partner.logo && <img src={partner.logo} alt="" loading="lazy" />}</span>
                  <span>{partner.name}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        <a className="pr__ask" href="/contact/">Ask about {product.name} <ArrowUpRight size={16} aria-hidden="true" /></a>
      </div>
    </article>
  )
}

function ProductView() {
  const { data: products, loading, error } = useApi(() => fetchList('/products/'), [], [])
  const ref = useRef(null)
  usePageMotion(ref, [products])
  return (
    <div ref={ref}>
      <PageHero
        page="product"
        eyebrow="Product"
        title="From prototype to product"
        description="Flagship products developed and manufactured under CRTDH, along with our commercialisation partners."
      />
      <section data-block="product.list" className="pr-page">
        <DataState loading={loading} error={error} data={products} emptyProps={{ title: 'Product profiles coming soon' }}>
          {(items) => (
            <>
              <nav className="pr-nav" aria-label="Products">
                <div className="container pr-nav__row">
                  {items.map((p) => <a key={p.id} href={`#${slug(p)}`}>{p.name}</a>)}
                </div>
              </nav>
              <div className="container">
                {items.map((p, k) => <ProductStage product={p} flip={k % 2 === 1} key={p.id} />)}
              </div>
            </>
          )}
        </DataState>
      </section>
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Product({ data }) {
  return (
    <PageDataProvider data={data}>
      <ProductView />
    </PageDataProvider>
  )
}
