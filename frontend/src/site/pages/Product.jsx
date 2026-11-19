import { PageDataProvider } from '../api/data.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import Carousel from '../components/Carousel'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'
import './Product.css'

function ProductView() {
  const { data: products, loading, error } = useApi(() => fetchList('/products/'), [], [])

  return (
    <div>
      <PageHero
        eyebrow="Product"
        title="From prototype to product"
        description="Flagship products developed and manufactured under CRTDH, along with our commercialisation partners."
      />

      <section data-block="product.list" className="section">
        <div className="container">
          <DataState loading={loading} error={error} data={products} emptyProps={{ title: 'Product profiles coming soon' }}>
            {(items) => (
              <div className="product-list">
                {items.map((product, i) => (
                  <Reveal as="article" className="product card" key={product.id} delay={Math.min(i, 4) * 0.06}>
                    {product.images && product.images.length > 0 && (
                      <div className="product__carousel">
                        <Carousel
                          items={product.images}
                          ariaLabel={`${product.name} images`}
                          renderItem={(img) => <img src={img.image} alt={product.name} />}
                        />
                      </div>
                    )}
                    <div className="product__body">
                      <h2>{product.name}</h2>
                      {product.partners && product.partners.length > 0 && (
                        <div className="product__partners">
                          <span className="product__partners-label">Commercialisation partners</span>
                          <div className="product__partners-list">
                            {product.partners.map((partner) => (
                              <span className="partner-chip" key={partner.id}>
                                {partner.logo && <img src={partner.logo} alt="" />}
                                {partner.name}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </Reveal>
                ))}
              </div>
            )}
          </DataState>
        </div>
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
