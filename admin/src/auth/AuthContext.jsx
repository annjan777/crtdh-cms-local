import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { auth } from '../api/cms.js';
import { ensureCsrf } from '../api/client.js';

// status: loading | signed-out | mfa | setup | signed-in | expired
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [status, setStatus] = useState('loading');
  const [user, setUser] = useState(null);

  useEffect(() => {
    let alive = true;
    ensureCsrf()
      .then(() => auth.me())
      .then((u) => {
        if (!alive) return;
        setUser(u);
        setStatus('signed-in');
      })
      .catch(() => alive && setStatus('signed-out'));
    const onExpired = () => setStatus((s) => (s === 'signed-in' ? 'expired' : s));
    window.addEventListener('crtdh:session-expired', onExpired);
    return () => {
      alive = false;
      window.removeEventListener('crtdh:session-expired', onExpired);
    };
  }, []);

  const login = useCallback(async (username, password) => {
    const res = await auth.login(username, password);
    if (res?.mfa_setup_required) setStatus('setup');
    else if (res?.mfa_required) setStatus('mfa');
    else {
      setUser(await auth.me());
      setStatus('signed-in');
    }
  }, []);

  const verifyMfa = useCallback(async (code) => {
    const u = await auth.mfa(code);
    setUser(u?.username ? u : await auth.me());
    setStatus('signed-in');
  }, []);

  const finishSetup = useCallback(async () => {
    setUser(await auth.me());
    setStatus('signed-in');
  }, []);

  const logout = useCallback(async () => {
    try {
      await auth.logout();
    } finally {
      setUser(null);
      setStatus('signed-out');
    }
  }, []);

  const value = useMemo(() => {
    const roles = user?.roles || [];
    return {
      status,
      user,
      setStatus,
      login,
      verifyMfa,
      finishSetup,
      logout,
      canPublish: roles.includes('publisher') || roles.includes('admin'),
      isAdmin: roles.includes('admin'),
    };
  }, [status, user, login, verifyMfa, finishSetup, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
