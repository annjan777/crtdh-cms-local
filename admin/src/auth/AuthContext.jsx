import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { auth } from '../api/cms.js';
import { ensureCsrf } from '../api/client.js';
import { nextFromLocation } from './next.js';
import { clearUserDrafts, setDraftOwner } from '../editor/drafts.js';

// status: loading | signed-out | mfa | setup | change-password | signed-in | expired
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [status, setStatus] = useState('loading');
  const [user, setUser] = useState(null);

  // A fully signed-in user: a temporary password must be changed first, and an
  // OAuth `next` (Django page) gets a full page navigation.
  const arrive = useCallback((u) => {
    setUser(u);
    setDraftOwner(u?.id);
    if (u?.must_change_password) return setStatus('change-password');
    const next = nextFromLocation();
    if (next) {
      window.location.assign(next);
      return undefined;
    }
    return setStatus('signed-in');
  }, []);

  useEffect(() => {
    let alive = true;
    ensureCsrf()
      .then(() => auth.me())
      .then((u) => {
        if (!alive) return;
        arrive(u);
      })
      .catch(() => alive && setStatus('signed-out'));
    const onExpired = () => setStatus((s) => (s === 'signed-in' ? 'expired' : s));
    window.addEventListener('crtdh:session-expired', onExpired);
    return () => {
      alive = false;
      window.removeEventListener('crtdh:session-expired', onExpired);
    };
  }, [arrive]);

  const login = useCallback(async (username, password) => {
    const res = await auth.login(username, password);
    if (res?.mfa_setup_required) setStatus('setup');
    else if (res?.mfa_required) setStatus('mfa');
    else arrive(await auth.me());
  }, [arrive]);

  const verifyMfa = useCallback(async (code) => {
    const u = await auth.mfa(code);
    arrive(u?.username ? u : await auth.me());
  }, [arrive]);

  const finishSetup = useCallback(async () => {
    arrive(await auth.me());
  }, [arrive]);

  const changePassword = useCallback(async (current, next) => {
    const u = await auth.changePassword(current, next);
    arrive(u?.username ? u : await auth.me());
  }, [arrive]);

  const signOutEverywhere = useCallback(async () => {
    try {
      await auth.revokeAllSessions();
    } catch {
      /* offline or already signed out: still sign out here */
    } finally {
      clearUserDrafts(user?.id);
      setDraftOwner(null);
      setUser(null);
      setStatus('signed-out');
    }
  }, [user]);

  const logout = useCallback(async () => {
    try {
      await auth.logout();
    } catch {
      /* offline or already signed out: still sign out here */
    } finally {
      clearUserDrafts(user?.id);
      setDraftOwner(null);
      setUser(null);
      setStatus('signed-out');
    }
  }, [user]);

  const value = useMemo(() => {
    const roles = user?.roles || [];
    return {
      status,
      user,
      setStatus,
      login,
      verifyMfa,
      finishSetup,
      changePassword,
      signOutEverywhere,
      logout,
      canPublish: roles.includes('publisher') || roles.includes('admin'),
      isAdmin: roles.includes('admin'),
    };
  }, [status, user, login, verifyMfa, finishSetup, changePassword, signOutEverywhere, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
