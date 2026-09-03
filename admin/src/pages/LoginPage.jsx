import { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Lock, LogIn, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!loading && user) {
    const dest = location.state?.from?.pathname || '/';
    return <Navigate to={dest} replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(username, password);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        setError('Incorrect username or password.');
      } else {
        setError('Could not sign in. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-panel">
        <div className="login-panel-mark" aria-hidden="true">
          C
        </div>
        <h2>CRTDH Content Admin</h2>
        <p>Manage every page of the CRTDH public site — team, innovations, facilities, media and more — from one place.</p>
      </div>

      <div className="login-form-side">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="login-brand">
            <span className="sidebar-logo">CRTDH</span>
            <span className="sidebar-subtitle">Admin sign in</span>
          </div>

          <label htmlFor="username">Username</label>
          <div className="input-with-icon">
            <User size={16} aria-hidden="true" />
            <input
              id="username"
              className="input"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>

          <label htmlFor="password">Password</label>
          <div className="input-with-icon">
            <Lock size={16} aria-hidden="true" />
            <input
              id="password"
              className="input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="form-error">{error}</div>}

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? (
              'Signing in…'
            ) : (
              <>
                <LogIn size={16} aria-hidden="true" />
                Sign in
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
