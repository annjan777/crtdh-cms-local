import { useEffect, useRef } from 'react'
import { motion, useInView, useMotionValue, useSpring } from 'framer-motion'

/**
 * Animated stat counter — counts up from 0 to `value` once it scrolls into
 * view. Used for homepage stats (team size, innovations, enterprises, ...).
 */
export default function Counter({ value = 0, suffix = '', prefix = '', duration = 1.6, className }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, amount: 0.6 })
  const motionValue = useMotionValue(0)
  const spring = useSpring(motionValue, { duration: duration * 1000, bounce: 0 })
  const displayRef = useRef(null)

  useEffect(() => {
    if (inView) motionValue.set(value)
  }, [inView, value, motionValue])

  useEffect(
    () =>
      spring.on('change', (latest) => {
        if (displayRef.current) {
          displayRef.current.textContent = `${prefix}${Math.round(latest).toLocaleString()}${suffix}`
        }
      }),
    [spring, prefix, suffix],
  )

  return (
    <motion.span ref={ref} className={className}>
      <span ref={displayRef}>{prefix}0{suffix}</span>
    </motion.span>
  )
}
