// Site-wide draft state: unpublished changes (drives the draft bar and the
// page status dots) and the publish in progress, polled until it ends.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { cms } from '../api/cms.js';

const ChangesContext = createContext(null);
const PUBLISH_KEY = 'crtdh-active-publish';
export const TERMINAL = new Set(['live', 'failed', 'cancelled']);
export const CANCELLABLE = new Set(['queued', 'ready_for_upload']);
const MAX_POLL_ERRORS = 6;

export function ChangesProvider({ children }) {
  const [changes, setChanges] = useState(null);
  const [pages, setPages] = useState(null);
  const [error, setError] = useState(null);
  const [publish, setPublish] = useState(null); // {id, status, step, message, live_at, agent_last_seen}
  const timer = useRef(null);

  const fetchNow = useCallback(async () => {
    try {
      const [c, p] = await Promise.all([cms.changes(), cms.pages()]);
      setChanges(c);
      setPages(p.pages);
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, []);

  const refresh = useCallback(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(fetchNow, 350);
  }, [fetchNow]);

  useEffect(() => {
    fetchNow();
    const onFocus = () => fetchNow();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [fetchNow]);

  // Poll a running publish; survive reloads via sessionStorage. Publish ids
  // are UUID strings. Ends on live / failed / cancelled; backs off on errors
  // and gives up after a run of them (a 404 means the id is gone).
  const stopPoll = useRef(null);
  const poll = useCallback(
    (id) => {
      stopPoll.current?.();
      const pid = String(id);
      let stopped = false;
      let errors = 0;
      sessionStorage.setItem(PUBLISH_KEY, pid);
      const tick = async () => {
        if (stopped) return;
        try {
          const st = await cms.publishStatus(pid);
          errors = 0;
          setPublish({ id: pid, ...st });
          if (TERMINAL.has(st.status)) {
            sessionStorage.removeItem(PUBLISH_KEY);
            fetchNow();
            return;
          }
        } catch (err) {
          errors += 1;
          setPublish((p) => ({ ...(p || { id: pid }), pollError: err }));
          if (err.code === 'CMS_NOT_FOUND' || errors >= MAX_POLL_ERRORS) {
            sessionStorage.removeItem(PUBLISH_KEY);
            setPublish((p) => ({ ...(p || { id: pid }), lost: true }));
            return;
          }
        }
        setTimeout(tick, errors ? Math.min(900 * 2 ** errors, 30000) : 900);
      };
      tick();
      const stop = () => {
        stopped = true;
      };
      stopPoll.current = stop;
      return stop;
    },
    [fetchNow],
  );

  useEffect(() => {
    const id = sessionStorage.getItem(PUBLISH_KEY);
    if (id) return poll(id);
    return undefined;
  }, [poll]);

  const cancelPublish = useCallback(async () => {
    if (!publish?.id) return null;
    try {
      const st = await cms.cancelPublish(publish.id);
      setPublish({ id: String(publish.id), ...st });
      if (TERMINAL.has(st.status)) {
        stopPoll.current?.();
        sessionStorage.removeItem(PUBLISH_KEY);
        fetchNow();
      }
      return null;
    } catch (err) {
      return err;
    }
  }, [publish, fetchNow]);

  const startPublish = useCallback(
    async (confirmShrink = false) => {
      try {
        const res = await cms.publish(confirmShrink);
        setPublish({ id: res.publish_id, status: res.status || 'queued', step: 'Waiting to start' });
        poll(res.publish_id);
        return null;
      } catch (err) {
        if (err.code === 'CMS_PUBLISH_RUNNING' && err.details?.publish_id) {
          poll(err.details.publish_id);
          return null;
        }
        return err;
      }
    },
    [poll],
  );

  const value = useMemo(() => {
    const count = changes?.count ?? 0;
    const pageCount = changes?.pages?.length ?? 0;
    return {
      changes,
      pages,
      error,
      count,
      pageCount,
      refresh,
      refreshNow: fetchNow,
      publish,
      startPublish,
      cancelPublish,
      clearPublish: () => setPublish(null),
      setChanges,
    };
  }, [changes, pages, error, refresh, fetchNow, publish, startPublish, cancelPublish]);

  return <ChangesContext.Provider value={value}>{children}</ChangesContext.Provider>;
}

export function useChanges() {
  return useContext(ChangesContext);
}
