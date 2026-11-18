// Centre column: the real public page in an iframe (preview.html), at a true
// 1280 px desktop width scaled to fit, or a 390 px phone width.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';

// Desktop renders at a real desktop width between 1024 and 1280 px, scaled to
// fit, so text stays readable on a 1280 px screen.
const widthFor = (device, avail) => (device === 'phone' ? 390 : Math.max(1024, Math.min(1280, Math.round(avail))));

export default function Canvas({ pageId, data, sections, selected, onSelect, device = 'desktop', interactive = true, title, fill = false }) {
  const frame = useRef(null);
  const wrap = useRef(null);
  const [ready, setReady] = useState(false);
  const [height, setHeight] = useState(900);
  const [avail, setAvail] = useState(1000);
  const scrollNext = useRef(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  const width = widthFor(device, avail);
  const scale = device === 'desktop' ? Math.min(1, avail / width) : 1;

  useLayoutEffect(() => {
    const el = wrap.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(() => setAvail(el.clientWidth - (device === 'phone' ? 0 : 0)));
    ro.observe(el);
    return () => ro.disconnect();
  }, [device]);

  useEffect(() => {
    const onMsg = (e) => {
      if (e.origin !== window.location.origin || e.source !== frame.current?.contentWindow) return;
      const m = e.data || {};
      if (m.type === 'ready') setReady(true);
      if (m.type === 'height') setHeight(m.height);
      if (m.type === 'select') onSelectRef.current?.(m.sectionId, m.pk, m.elsewhere);
      if (m.type === 'selected-top') {
        const scroller = wrap.current?.closest('[data-scroll]');
        if (scroller) {
          const top = wrap.current.offsetTop + m.top * scale - 24;
          if (top < scroller.scrollTop || top > scroller.scrollTop + scroller.clientHeight - 120) scroller.scrollTo({ top, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
        }
      }
    };
    window.addEventListener('message', onMsg);
    return () => window.removeEventListener('message', onMsg);
  }, [scale]);

  // Scroll to the selection only when it changes, not on every keystroke.
  const selKey = selected ? `${selected.sectionId}:${selected.pk ?? ''}` : '';
  useEffect(() => {
    scrollNext.current = true;
  }, [selKey]);

  const send = useCallback(() => {
    if (!ready || !data) return;
    const scrollToSelected = scrollNext.current;
    scrollNext.current = false;
    frame.current?.contentWindow?.postMessage({ type: 'render', pageId, data, sections, selected, interactive, scrollToSelected }, window.location.origin);
  }, [ready, data, pageId, sections, selected, interactive]);
  useEffect(send, [send]);

  return (
    <div ref={wrap} className={`canvas-frame device-${device}${fill ? ' is-fill' : ''}`} style={{ height: fill ? undefined : height * scale }}>
      <iframe
        ref={frame}
        src="/preview.html"
        title={title}
        style={{ width, height: fill ? '100%' : height, transform: scale !== 1 ? `scale(${scale})` : undefined, transformOrigin: '0 0' }}
      />
    </div>
  );
}
