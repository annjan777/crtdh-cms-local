import { motion } from 'framer-motion'

const DIRECTIONS = {
  up: { y: 28, x: 0 },
  down: { y: -28, x: 0 },
  left: { y: 0, x: 28 },
  right: { y: 0, x: -28 },
  none: { y: 0, x: 0 },
}

/**
 * Scroll-triggered reveal wrapper (framer-motion `whileInView`). Used
 * throughout the site so sections/cards animate in once as the visitor
 * scrolls, instead of everything popping in on load.
 */
export default function Reveal({
  children,
  as = 'div',
  direction = 'up',
  delay = 0,
  duration = 0.6,
  distance,
  once = true,
  amount = 0.2,
  className,
  style,
  ...rest
}) {
  const Component = motion[as] || motion.div
  const dir = DIRECTIONS[direction] || DIRECTIONS.up
  const offset = distance ?? 1

  return (
    <Component
      className={className}
      style={style}
      initial={{ opacity: 0, x: dir.x * offset, y: dir.y * offset }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once, amount }}
      transition={{ duration, delay, ease: [0.16, 1, 0.3, 1] }}
      {...rest}
    >
      {children}
    </Component>
  )
}

/** Stagger container — pair with <StaggerItem> children. */
export function Stagger({ children, as = 'div', className, style, stagger = 0.08, once = true, amount = 0.2, ...rest }) {
  const Component = motion[as] || motion.div
  return (
    <Component
      className={className}
      style={style}
      initial="hidden"
      whileInView="show"
      viewport={{ once, amount }}
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: stagger } },
      }}
      {...rest}
    >
      {children}
    </Component>
  )
}

export const staggerItem = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] } },
}

export function StaggerItem({ as = 'div', className, style, children, ...rest }) {
  const Component = motion[as] || motion.div
  return (
    <Component className={className} style={style} variants={staggerItem} {...rest}>
      {children}
    </Component>
  )
}
