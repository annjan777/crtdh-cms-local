import { useRef } from 'react'
import { motion, useMotionTemplate, useSpring } from 'framer-motion'

/**
 * Mouse-tracked 3D tilt wrapper. Pure CSS-3D-via-transform — no WebGL,
 * so it's cheap and works everywhere. Wrap any card in this to get a
 * subtle perspective tilt + a light "glare" following the cursor.
 */
export default function TiltCard({ children, className = '', max = 8, glare = true, scale = 1.015, style, ...rest }) {
  const ref = useRef(null)
  const rotateX = useSpring(0, { stiffness: 260, damping: 22, mass: 0.6 })
  const rotateY = useSpring(0, { stiffness: 260, damping: 22, mass: 0.6 })
  const glareX = useSpring(50, { stiffness: 260, damping: 30 })
  const glareY = useSpring(50, { stiffness: 260, damping: 30 })

  function handleMove(e) {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const px = (e.clientX - rect.left) / rect.width
    const py = (e.clientY - rect.top) / rect.height
    rotateY.set((px - 0.5) * max * 2)
    rotateX.set(-(py - 0.5) * max * 2)
    glareX.set(px * 100)
    glareY.set(py * 100)
  }

  function handleLeave() {
    rotateX.set(0)
    rotateY.set(0)
    glareX.set(50)
    glareY.set(50)
  }

  const glareBackground = useMotionTemplate`radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255,255,255,0.35), transparent 55%)`

  return (
    <motion.div
      ref={ref}
      className={`tilt ${className}`}
      style={{ position: 'relative', rotateX, rotateY, scale: 1, ...style }}
      whileHover={{ scale }}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      {...rest}
    >
      {children}
      {glare && (
        <motion.span
          aria-hidden="true"
          style={{
            position: 'absolute',
            inset: 0,
            background: glareBackground,
            pointerEvents: 'none',
            borderRadius: 'inherit',
            mixBlendMode: 'overlay',
          }}
        />
      )}
    </motion.div>
  )
}
