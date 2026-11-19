// The canvas iframe. It renders the public page with its own styles (so the
// page's media queries see the real Desktop / Phone width) and turns
// `[data-cms-section]` elements into selectable targets: outline on hover or
// keyboard focus only, Enter or click selects. Talks to the editor through
// same-origin postMessage.
import { StrictMode, useEffect, useLayoutEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import SitePreview from './SitePreview.jsx';
import { CmsPreviewContext } from './cms-context.js';
import { tagSections } from './section-map.js';

const EDITOR_CSS = `
html,body{margin:0}
[data-cms-section]{position:relative;cursor:pointer;scroll-margin-top:24px}
html.cms-interactive [data-cms-section]:hover,html.cms-interactive [data-cms-section]:focus-visible{outline:2px solid #2bb3b3;outline-offset:-2px}
html.cms-interactive [data-cms-section]:focus-visible{outline:3px solid #137272}
html.cms-interactive [data-cms-section][data-cms-selected]{outline:2px solid #1a8a8a;outline-offset:-2px}
html.cms-interactive [data-cms-section][data-cms-selected]::before{content:attr(data-cms-tag);position:absolute;z-index:20;top:10px;left:10px;background:#1a8a8a;color:#fff;font:600 13px/1.2 "IBM Plex Sans",system-ui,sans-serif;padding:4px 8px;border-radius:4px;pointer-events:none}
html.cms-interactive [data-cms-section]:hover:not([data-cms-selected])::before{content:attr(data-cms-tag);position:absolute;z-index:20;top:10px;left:10px;background:#fff;color:#0b3a5a;border:1px solid #2bb3b3;font:600 13px/1.2 "IBM Plex Sans",system-ui,sans-serif;padding:3px 7px;border-radius:4px;pointer-events:none}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation:none!important;transition:none!important}}
`;

const post = (msg) => window.parent?.postMessage(msg, window.location.origin);

function App() {
  const [state, setState] = useState(null);

  useEffect(() => {
    const onMsg = (e) => {
      if (e.origin !== window.location.origin || e.source !== window.parent) return;
      if (e.data?.type === 'render') setState(e.data);
    };
    window.addEventListener('message', onMsg);
    post({ type: 'ready' });
    return () => window.removeEventListener('message', onMsg);
  }, []);

  // Make sections reachable by keyboard and mark the selected one.
  useLayoutEffect(() => {
    if (!state) return;
    document.documentElement.classList.toggle('cms-interactive', !!state.interactive);
    const labels = Object.fromEntries((state.sections || []).map((s) => [s.id, s.label]));
    // The real public components carry no editor markup: tag their blocks with section ids.
    tagSections(document.getElementById('preview-root'), state.pageId, labels);
    let selectedEl = null;
    for (const el of document.querySelectorAll('[data-cms-section]')) {
      const id = el.getAttribute('data-cms-section');
      if (state.interactive) {
        el.setAttribute('tabindex', '0');
        el.setAttribute('aria-label', `Edit section: ${labels[id] || el.getAttribute('data-cms-tag') || id}`);
      } else {
        el.removeAttribute('tabindex');
        el.removeAttribute('aria-label');
      }
      const isSel = state.selected?.sectionId === id;
      el.toggleAttribute('data-cms-selected', !!isSel);
      if (isSel) selectedEl = el;
    }
    if (selectedEl && state.scrollToSelected) post({ type: 'selected-top', top: selectedEl.getBoundingClientRect().top + window.scrollY });
  }, [state]);

  // Report height so the editor can size and scale the frame.
  useEffect(() => {
    const ro = new ResizeObserver(() => post({ type: 'height', height: document.documentElement.scrollHeight }));
    ro.observe(document.body);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const pick = (target) => {
      const sec = target.closest?.('[data-cms-section]');
      if (!sec) return false;
      const item = target.closest('[data-cms-item]');
      post({ type: 'select', sectionId: sec.getAttribute('data-cms-section'), pk: item ? Number(item.getAttribute('data-cms-item')) : null, elsewhere: sec.getAttribute('data-cms-elsewhere') });
      return true;
    };
    const onClick = (e) => {
      // Links never navigate inside the preview.
      if (e.target.closest('a')) e.preventDefault();
      if (state?.interactive) pick(e.target);
    };
    const onKey = (e) => {
      if (!state?.interactive) return;
      if ((e.key === 'Enter' || e.key === ' ') && e.target.matches?.('[data-cms-section]')) {
        e.preventDefault();
        pick(e.target);
      }
      if (e.key === 'Escape') post({ type: 'escape' });
    };
    document.addEventListener('click', onClick, true);
    document.addEventListener('keydown', onKey);
    const onSubmit = (e) => e.preventDefault();
    document.addEventListener('submit', onSubmit, true);
    return () => {
      document.removeEventListener('click', onClick, true);
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('submit', onSubmit, true);
    };
  }, [state?.interactive]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!state?.data) return null;
  return (
    <CmsPreviewContext.Provider value={{ sections: state.sections || [], selected: state.selected, pageId: state.pageId }}>
      <SitePreview pageId={state.pageId} data={state.data} />
    </CmsPreviewContext.Provider>
  );
}

const style = document.createElement('style');
style.textContent = EDITOR_CSS;
document.head.appendChild(style);
document.documentElement.style.overflow = 'hidden';
createRoot(document.getElementById('preview-root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
