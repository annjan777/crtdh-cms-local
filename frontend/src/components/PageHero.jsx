import { motion } from 'framer-motion'
import './PageHero.css'

export default function PageHero({ eyebrow, title, description }) {
  return (
    <div className="page-hero">
      <div className="page-hero__mesh" aria-hidden="true" />
      <div className="page-hero__grid" aria-hidden="true" />
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
