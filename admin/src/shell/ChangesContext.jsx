// Site-wide draft state: unpublished changes (drives the draft bar and the
// page status dots) and the publish in progress, polled until it ends.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { cms } from '../api/cms.js';

const ChangesContext = createContext(null);
const PUBLISH_KEY = 'crtdh-active-publish';

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

  // Poll a running publish; survive reloads via sessionStorage.
  const poll = useCallback(
    (id) => {
      let stopped = false;
      sessionStorage.setItem(PUBLISH_KEY, String(id));
      const tick = async () => {
        if (stopped) return;
        try {
          const st = await cms.publishStatus(id);
          setPublish({ id, ...st });
          if (st.status === 'live' || st.status === 'failed') {
            sessionStorage.removeItem(PUBLISH_KEY);
            fetchNow();
            return;
          }
        } catch (err) {
          setPublish((p) => ({ ...(p || { id }), pollError: err }));
        }
        setTimeout(tick, 900);
      };
      tick();
      return () => {
        stopped = true;
      };
    },
    [fetchNow],
  );

  useEffect(() => {
    const id = sessionStorage.getItem(PUBLISH_KEY);
    if (id) return poll(Number(id));
    return undefined;
  }, [poll]);

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
      clearPublish: () => setPublish(null),
      setChanges,
    };
  }, [changes, pages, error, refresh, fetchNow, publish, startPublish]);

  return <ChangesContext.Provider value={value}>{children}</ChangesContext.Provider>;
}

export function useChanges() {
  return useContext(ChangesContext);
}
