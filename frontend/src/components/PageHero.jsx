import { motion } from 'framer-motion'
import './PageHero.css'

/**
 * Page banner. With `image`, the photo sits on the right at its own aspect ratio and a navy
 * gradient overlay (not baked into the photo) keeps the title readable on the left.
 */
export default function PageHero({ eyebrow, title, description, image, imagePosition }) {
  return (
    <div className={`page-hero${image ? ' page-hero--photo' : ''}`}>
      {image ? (
        <>
          <img
            className="page-hero__photo"
            src={image}
            alt=""
            style={{ objectPosition: imagePosition || 'center center' }}
          />
          <div className="page-hero__overlay" aria-hidden="true" />
        </>
      ) : (
        <>
          <div className="page-hero__mesh" aria-hidden="true" />
          <div className="page-hero__grid" aria-hidden="true" />
        </>
      )}
      <div className="container page-hero__inner">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
        >
          {eyebrow && <span className="eyebrow eyebrow--on-dark">{eyebrow}</span>}
          <h1>{title}</h1>
          {description && <p className="page-hero__desc">{description}</p>}
        </motion.div>
      </div>
    </div>
  )
}
