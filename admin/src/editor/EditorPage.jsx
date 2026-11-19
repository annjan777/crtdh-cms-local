// Pattern 8 — Split pane: pages + numbered sections (left), the real page
// (centre), the selected section's fields (right). Below 1024 px the canvas
// is replaced by the section list, and Preview opens the page full screen.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useBlocker, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Monitor, Smartphone, X } from 'lucide-react';
import AppShell, { PageNav } from '../shell/AppShell.jsx';
import { useChanges } from '../shell/ChangesContext.jsx';
import { Banner, Dialog, ErrorPanel } from '../ui/index.jsx';
import { EditorProvider, hasUnsaved, useEditor } from './EditorContext.jsx';
import Canvas from './Canvas.jsx';
import FieldPanel from './FieldPanel.jsx';

function useWide() {
  const q = '(min-width: 1024px)';
  const [wide, setWide] = useState(() => window.matchMedia(q).matches);
  useEffect(() => {
    const m = window.matchMedia(q);
    const on = () => setWide(m.matches);
    m.addEventListener('change', on);
    return () => m.removeEventListener('change', on);
  }, []);
  return wide;
}

function DeviceToggle({ device, setDevice }) {
  return (
    <div className="segmented" role="group" aria-label="Preview width">
      <button type="button" aria-pressed={device === 'desktop'} onClick={() => setDevice('desktop')}>
        <Monitor size={16} aria-hidden="true" /> Desktop
      </button>
      <button type="button" aria-pressed={device === 'phone'} onClick={() => setDevice('phone')}>
        <Smartphone size={16} aria-hidden="true" /> Phone
      </button>
    </div>
  );
}

export function PreviewOverlay({ open, onClose, page, data, sections }) {
  const [device, setDevice] = useState('desktop');
  return (
    <Dialog open={open} onClose={onClose} size="full" title={`Preview of ${page?.title || ''}`} initialFocus="close">
      <div className="preview-overlay">
        <div className="preview-bar">
          <p>
            <strong>Preview · {page?.title}</strong> <span className="muted">Includes unpublished changes. Not live yet.</span>
          </p>
          <DeviceToggle device={device} setDevice={setDevice} />
          <button type="button" className="btn" data-autofocus="close" onClick={onClose}>
            <X size={16} aria-hidden="true" /> Close preview
          </button>
        </div>
        <div className="preview-scroll" data-scroll>
          {data ? <Canvas pageId={page.id} data={data} sections={sections} selected={null} device={device} interactive={false} title={`Preview of the ${page.title} page`} /> : null}
        </div>
      </div>
    </Dialog>
  );
}

function SectionCards({ sections, onSelect }) {
  return (
    <ol className="section-cards" aria-label="Sections on this page">
      {sections.map((s, i) => (
        <li key={s.id}>
          <button type="button" onClick={() => onSelect(s.id)}>
            <span className="num">{i + 1}</span>
            <span>
              <span className="section-name">{s.label}</span>
              <span className="item-sub">{s.kind === 'collection' ? `${s.items.length} ${s.items.length === 1 ? s.item_noun || s.add_label : `${s.item_noun || s.add_label}s`}` : s.description}</span>
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}

function EditorSkeleton() {
  return (
    <div className="canvas-skeleton" aria-hidden="true">
      <div className="skel" style={{ height: 320 }} />
      <div className="skel skel-line" style={{ width: '40%', marginTop: 28 }} />
      <div className="skel skel-line" style={{ width: '70%' }} />
      <div className="skel skel-line" style={{ width: '62%' }} />
      <div className="skel" style={{ height: 160, marginTop: 28 }} />
    </div>
  );
}

function PanelSkeleton() {
  return (
    <aside className="field-panel" aria-busy="true" aria-label="Loading section">
      <div className="skel skel-line" style={{ width: '50%', height: 20 }} />
      <div className="skel skel-line" style={{ width: '70%' }} />
      {[0, 1, 2].map((i) => (
        <div key={i} style={{ marginTop: 22 }}>
          <div className="skel skel-line" style={{ width: '30%' }} />
          <div className="skel" style={{ height: 40 }} />
        </div>
      ))}
    </aside>
  );
}

function Editor() {
  const { page, preview, loadError, reload, records, restored, dismissRestored, online } = useEditor();
  const { pages } = useChanges();
  const { pageId } = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const wide = useWide();
  const [device, setDevice] = useState('desktop');
  const [navOpen, setNavOpen] = useState(false);
  const sectionId = params.get('section');
  const itemPk = params.get('item') ? Number(params.get('item')) : null;
  const previewOpen = params.get('preview') === '1';

  const sections = page?.sections || [];
  const section = sections.find((s) => s.id === sectionId) || (wide ? sections[0] : null);
  const index = section ? sections.indexOf(section) : -1;
  const meta = pages?.find((p) => p.id === pageId);

  const select = useCallback(
    (sid, pk, elsewhere) => {
      if (elsewhere && elsewhere !== pageId) {
        navigate(`/pages/${elsewhere}?section=${encodeURIComponent(sid)}`);
        return;
      }
      const next = new URLSearchParams(params);
      next.set('section', sid);
      if (pk) next.set('item', String(pk));
      else next.delete('item');
      setParams(next, { replace: false });
      setTimeout(() => document.getElementById('panel-title')?.focus({ preventScroll: true }), 0);
    },
    [params, setParams, pageId, navigate],
  );
  const selectItem = (pk) => {
    const next = new URLSearchParams(params);
    if (section) next.set('section', section.id);
    if (pk) next.set('item', String(pk));
    else next.delete('item');
    setParams(next);
  };
  const setPreview = (on) => {
    const next = new URLSearchParams(params);
    if (on) next.set('preview', '1');
    else next.delete('preview');
    setParams(next);
  };

  // Guard: in-flight or failed saves.
  const unsaved = hasUnsaved(records);
  const blocker = useBlocker(({ currentLocation, nextLocation }) => unsaved && currentLocation.pathname !== nextLocation.pathname);
  useEffect(() => {
    if (!unsaved) return undefined;
    const h = (e) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', h);
    return () => window.removeEventListener('beforeunload', h);
  }, [unsaved]);

  const selected = section ? { sectionId: section.id, pk: section.kind === 'collection' ? itemPk || section.items[0]?.pk : null } : null;
  const canvasSections = useMemo(() => sections.map(({ items: _i, ...s }) => s), [sections]);
  const navSections = useMemo(() => sections.map((s) => ({ id: s.id, label: s.label })), [sections]);

  const title = page?.title || meta?.title || '';
  const nav = <PageNav sections={navSections} selectedSection={section?.id} onSelectSection={(id) => { select(id); setNavOpen(false); }} onNavigate={() => setNavOpen(false)} />;

  return (
    <AppShell crumb={title} onOpenNav={wide ? null : () => setNavOpen(true)}>
      <div className={`editor${wide ? ' is-wide' : ' is-narrow'}`}>
        {wide ? <div className="col-nav">{nav}</div> : null}
        {!wide ? (
          <Dialog open={navOpen} onClose={() => setNavOpen(false)} size="drawer" title="Pages" initialFocus="close-nav">
            <button type="button" className="btn drawer-close" data-autofocus="close-nav" onClick={() => setNavOpen(false)}>
              <X size={16} aria-hidden="true" /> Close
            </button>
            {nav}
          </Dialog>
        ) : null}
        <main id="main" className="col-main" tabIndex={-1}>
          {!online ? <Banner tone="warn">You’re offline. Keep typing: your text is kept on this computer and saves when the connection is back.</Banner> : null}
          {restored ? (
            <Banner tone="info" actions={<button type="button" className="btn btn-small" onClick={dismissRestored}>Dismiss</button>}>
              Restored {restored} unsaved change{restored === 1 ? '' : 's'} from this computer. {restored === 1 ? 'It is' : 'They are'} being saved now.
            </Banner>
          ) : null}
          {loadError ? (
            <ErrorPanel error={loadError} onRetry={() => reload()} title={`The ${title || 'page'} editor couldn’t be loaded`} />
          ) : wide ? (
            <>
              <div className="canvas-bar">
                <h1 className="canvas-title">{title}</h1>
                <p className="muted canvas-hint">Click any part of the page to edit it.</p>
                <DeviceToggle device={device} setDevice={setDevice} />
              </div>
              <div className="canvas-scroll" data-scroll tabIndex={0} role="region" aria-label={`${title || 'Page'} page, scrollable`}>
                {page && preview ? (
                  <Canvas pageId={pageId} data={preview} sections={canvasSections} selected={selected} onSelect={select} device={device} title={`${title} page. Select a section to edit it.`} />
                ) : (
                  <EditorSkeleton />
                )}
              </div>
            </>
          ) : (
            <div className="narrow-main">
              {section ? (
                <button type="button" className="btn back-btn" onClick={() => setParams(new URLSearchParams())}>
                  ← All sections of {title}
                </button>
              ) : (
                <>
                  <div className="canvas-bar">
                    <h1 className="canvas-title">{title}</h1>
                    <button type="button" className="btn" onClick={() => setPreview(true)}>
                      Preview page
                    </button>
                  </div>
                  {page ? <SectionCards sections={sections} onSelect={(id) => select(id)} /> : <EditorSkeleton />}
                </>
              )}
              {section ? <FieldPanel section={section} index={index} total={sections.length} selectedPk={itemPk} onSelectItem={selectItem} pageTitle={title} /> : null}
            </div>
          )}
        </main>
        {wide && !loadError ? page ? <FieldPanel section={section} index={index} total={sections.length} selectedPk={itemPk} onSelectItem={selectItem} pageTitle={title} /> : <PanelSkeleton /> : null}
      </div>
      <PreviewOverlay open={previewOpen && !!page} onClose={() => setPreview(false)} page={page} data={preview} sections={canvasSections} />
      <Dialog
        open={blocker.state === 'blocked'}
        onClose={() => blocker.reset?.()}
        title="Leave before your change is saved?"
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => blocker.reset?.()}>
              Stay on this page
            </button>
            <button type="button" className="btn btn-danger" onClick={() => blocker.proceed?.()}>
              Leave anyway
            </button>
          </>
        }
      >
        <p>A change on this page hasn’t been saved yet. Its text is kept on this computer and is restored when you come back, but it isn’t in the CMS until it saves.</p>
      </Dialog>
    </AppShell>
  );
}

export default function EditorPage() {
  const { pageId } = useParams();
  return (
    <EditorProvider pageId={pageId} key={pageId}>
      <Editor />
    </EditorProvider>
  );
}
