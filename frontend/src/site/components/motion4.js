import { useEffect } from 'react'

const reduced = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/**
 * Scroll reveals for `[data-rv]` elements inside `rootRef`. Content is never hidden before the script runs:
 * an element is only "armed" (hidden) by JavaScript when it is still below the fold, then revealed once.
 */
export function useReveals(rootRef, deps = []) {
  useEffect(() => {
    const root = rootRef.current
    if (!root || reduced() || !('IntersectionObserver' in window)) return undefined
    const els = Array.from(root.querySelectorAll('[data-rv]'))
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('rv-in')
          io.unobserve(e.target)
        }
      })
    }, { rootMargin: '0px 0px -12% 0px' })
    els.forEach((el) => {
      const r = el.getBoundingClientRect()
      if (r.top > window.innerHeight * 0.92) {
        el.classList.add('rv-armed')
        io.observe(el)
      }
    })
    return () => io.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

/** Parallax for `[data-px]` elements (value = fraction of scroll), at most two per page. */
export function useParallax(rootRef, deps = []) {
  useEffect(() => {
    const root = rootRef.current
    if (!root || reduced()) return undefined
    const els = Array.from(root.querySelectorAll('[data-px]')).slice(0, 2)
    if (!els.length) return undefined
    let ticking = false
    const update = () => {
      ticking = false
      els.forEach((el) => {
        const box = el.parentElement.getBoundingClientRect()
        if (box.bottom < 0 || box.top > window.innerHeight) return
        const k = parseFloat(el.getAttribute('data-px')) || 0.1
        const mode = el.getAttribute('data-px-mode')
        const off = mode === 'top' ? -box.top * k : (box.top + box.height / 2 - window.innerHeight / 2) * -k
        el.style.transform = `translate3d(0, ${off.toFixed(1)}px, 0)`
      })
    }
    const onScroll = () => {
      if (!ticking) {
        ticking = true
        requestAnimationFrame(update)
      }
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

export const prefersReducedMotion = reduced
