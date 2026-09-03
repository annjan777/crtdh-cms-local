import { Component, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import './HeroScene.css'

// --- WebGL feature detection -------------------------------------------------
function supportsWebGL() {
  try {
    const canvas = document.createElement('canvas')
    return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')))
  } catch {
    return false
  }
}

// --- Error boundary: any r3f/three runtime failure falls back to CSS mesh ---
class SceneErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  componentDidCatch(error) {
    console.warn('[HeroScene] WebGL scene failed, falling back to CSS mesh:', error)
  }
  render() {
    if (this.state.hasError) return this.props.fallback
    return this.props.children
  }
}

// A cloud of nodes connected to their nearest neighbours — evokes a
// research / molecular / data-network motif without being literal.
function NodeNetwork({ count = 90, radius = 4.2 }) {
  const groupRef = useRef(null)
  const pointsRef = useRef(null)

  const { positions, linePositions } = useMemo(() => {
    const pts = []
    for (let i = 0; i < count; i += 1) {
      // Distribute inside a sphere with a soft bias toward the surface (shell-like).
      const u = Math.random()
      const v = Math.random()
      const theta = 2 * Math.PI * u
      const phi = Math.acos(2 * v - 1)
      const r = radius * (0.55 + 0.45 * Math.random())
      pts.push(
        new THREE.Vector3(
          r * Math.sin(phi) * Math.cos(theta),
          r * Math.sin(phi) * Math.sin(theta) * 0.7,
          r * Math.cos(phi),
        ),
      )
    }

    const positions = new Float32Array(pts.length * 3)
    pts.forEach((p, i) => {
      positions[i * 3] = p.x
      positions[i * 3 + 1] = p.y
      positions[i * 3 + 2] = p.z
    })

    // Connect each node to its 2 nearest neighbours (cheap O(n^2), n is small).
    const lineVerts = []
    const maxDist = radius * 0.85
    for (let i = 0; i < pts.length; i += 1) {
      const dists = []
      for (let j = 0; j < pts.length; j += 1) {
        if (i === j) continue
        dists.push([j, pts[i].distanceTo(pts[j])])
      }
      dists.sort((a, b) => a[1] - b[1])
      dists.slice(0, 2).forEach(([j, d]) => {
        if (d < maxDist) {
          lineVerts.push(pts[i].x, pts[i].y, pts[i].z, pts[j].x, pts[j].y, pts[j].z)
        }
      })
    }

    return { positions, linePositions: new Float32Array(lineVerts) }
  }, [count, radius])

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.06
      groupRef.current.rotation.x = Math.sin(Date.now() * 0.00005) * 0.15
    }
    if (pointsRef.current) {
      pointsRef.current.material.size = 0.055 + Math.sin(Date.now() * 0.0012) * 0.008
    }
  })

  return (
    <group ref={groupRef}>
      <lineSegments>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[linePositions, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color="#3ab3a8" transparent opacity={0.28} />
      </lineSegments>
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        </bufferGeometry>
        <pointsMaterial color="#f5ab52" size={0.06} sizeAttenuation transparent opacity={0.9} />
      </points>
    </group>
  )
}

function Scene() {
  return (
    <>
      <ambientLight intensity={0.6} />
      <NodeNetwork />
    </>
  )
}

/**
 * Lightweight r3f hero accent: an abstract rotating node network. Pauses its
 * render loop when scrolled off-screen, caps device pixel ratio, and never
 * blocks content — if WebGL is unavailable or the scene errors, it renders
 * nothing and the CSS gradient-mesh background (already behind it) carries
 * the visual on its own.
 */
export default function HeroScene({ className = '' }) {
  const containerRef = useRef(null)
  const [active, setActive] = useState(true)
  const [canRender, setCanRender] = useState(false)

  useEffect(() => {
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion) return
    setCanRender(supportsWebGL())
  }, [])

  useEffect(() => {
    const node = containerRef.current
    if (!node || !canRender) return undefined
    const observer = new IntersectionObserver(
      ([entry]) => setActive(entry.isIntersecting),
      { threshold: 0.05 },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [canRender])

  if (!canRender) return null

  return (
    <div ref={containerRef} className={`hero-scene ${className}`} aria-hidden="true">
      <SceneErrorBoundary fallback={null}>
        <Suspense fallback={null}>
          <Canvas
            dpr={[1, 1.5]}
            frameloop={active ? 'always' : 'never'}
            gl={{ antialias: true, alpha: true, powerPreference: 'low-power' }}
            camera={{ position: [0, 0, 9], fov: 45 }}
          >
            <Scene />
          </Canvas>
        </Suspense>
      </SceneErrorBoundary>
    </div>
  )
}
