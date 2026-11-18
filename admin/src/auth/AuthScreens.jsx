// Pattern 3 — Form (auth): a centred card, no app chrome.
// Sign in → authenticator code, or first-time enrolment (QR → confirm →
// recovery codes). Also covers lockout and "signed out after inactivity".
import { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import { useAuth } from './AuthContext.jsx';
import { auth } from '../api/cms.js';
import { Banner, Field, Spinner, fmtTime } from '../ui/index.jsx';

function Card({ title, lead, children }) {
  return (
    <main className="auth-page" id="main">
      <div className="auth-card">
        <div className="auth-brand">
          <img src="/apple-touch-icon.png" alt="" width="36" height="36" />
          <span>CRTDH website editor</span>
        </div>
        <h1>{title}</h1>
        {lead ? <p className="auth-lead">{lead}</p> : null}
        {children}
      </div>
      <p className="auth-foot">For CRTDH, IIT Kharagpur staff. Trouble signing in? Ask an Admin.</p>
    </main>
  );
}

function SubmitButton({ busy, children }) {
  return (
    <button type="submit" className="btn btn-primary btn-block" aria-busy={busy || undefined}>
      {busy ? <Spinner /> : null}
      {children}
    </button>
  );
}

function SignIn({ expired }) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [touched, setTouched] = useState({});
  const [error, setError] = useState(null);
  const [locked, setLocked] = useState(null);
  const [busy, setBusy] = useState(false);
  const userRef = useRef(null);
  const passRef = useRef(null);

  const missing = { username: !username.trim(), password: !password };
  const showErr = (k) => touched[k] && missing[k];

  async function submit(e) {
    e.preventDefault();
    setTouched({ username: true, password: true });
    if (missing.username) return userRef.current?.focus();
    if (missing.password) return passRef.current?.focus();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
    } catch (err) {
      if (err.code === 'CMS_RATE_LIMITED') setLocked(err);
      else setError(err);
      setPassword('');
    } finally {
      setBusy(false);
    }
  }

  if (locked) {
    const until = locked.details?.locked_until;
    return (
      <Card title="Sign-in is paused" lead={locked.message}>
        <Banner tone="warn">
          {until ? <>You can try again at {fmtTime(until)}. </> : null}
          {locked.fix}
        </Banner>
        <button type="button" className="btn btn-block" onClick={() => setLocked(null)}>
          Back to sign in
        </button>
      </Card>
    );
  }

  return (
    <Card
      title={expired ? 'Sign in again' : 'Sign in'}
      lead={expired ? 'You were signed out after 30 minutes without activity. Text you hadn’t saved is kept on this computer and saves once you’re back.' : 'Edit the CRTDH website and publish changes.'}
    >
      {error ? (
        <Banner tone="danger">
          {error.message} {error.fix}
        </Banner>
      ) : null}
      <form onSubmit={submit} noValidate>
        <Field label="Username" htmlFor="username" error={showErr('username') ? 'Enter your username.' : null}>
          <input
            ref={userRef}
            id="username"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            value={username}
            aria-invalid={showErr('username') || undefined}
            aria-describedby="username-msg"
            onChange={(e) => setUsername(e.target.value)}
            onBlur={() => setTouched((t) => ({ ...t, username: true }))}
            onFocus={() => setTouched((t) => ({ ...t, username: false }))}
          />
        </Field>
        <Field label="Password" htmlFor="password" error={showErr('password') ? 'Enter your password.' : null}>
          <input
            ref={passRef}
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            aria-invalid={showErr('password') || undefined}
            aria-describedby="password-msg"
            onChange={(e) => setPassword(e.target.value)}
            onBlur={() => setTouched((t) => ({ ...t, password: true }))}
            onFocus={() => setTouched((t) => ({ ...t, password: false }))}
          />
        </Field>
        <SubmitButton busy={busy}>Sign in</SubmitButton>
      </form>
    </Card>
  );
}

function CodeInput({ id, value, onChange, error, inputRef, recovery }) {
  return (
    <input
      ref={inputRef}
      id={id}
      name="code"
      className="code-input"
      inputMode={recovery ? 'text' : 'numeric'}
      autoComplete="one-time-code"
      maxLength={recovery ? 9 : 6}
      placeholder={recovery ? 'xxxx-xxxx' : '123456'}
      value={value}
      aria-invalid={!!error || undefined}
      aria-describedby={`${id}-msg`}
      onChange={(e) => onChange(recovery ? e.target.value.trim().toLowerCase() : e.target.value.replace(/\D/g, ''))}
    />
  );
}

function Mfa() {
  const { verifyMfa, setStatus } = useAuth();
  const [code, setCode] = useState('');
  const [recovery, setRecovery] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const ref = useRef(null);
  useEffect(() => ref.current?.focus(), [recovery]);

  async function submit(e) {
    e.preventDefault();
    if (!recovery && code.length !== 6) {
      setError('Enter the 6-digit code from your authenticator app.');
      return ref.current?.focus();
    }
    setBusy(true);
    setError(null);
    try {
      await verifyMfa(code);
    } catch (err) {
      if (err.code === 'CMS_UNAUTHENTICATED') setStatus('signed-out');
      setError(`${err.message} ${err.fix}`);
      setCode('');
      ref.current?.focus();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Enter your code" lead={recovery ? 'Enter one of the recovery codes you saved when you set up sign-in. Each works once.' : 'Open your authenticator app and enter the 6-digit code for CRTDH CMS.'}>
      <form onSubmit={submit} noValidate>
        <Field label={recovery ? 'Recovery code' : 'Code'} htmlFor="code" error={error}>
          <CodeInput id="code" value={code} onChange={(v) => { setCode(v); setError(null); }} error={error} inputRef={ref} recovery={recovery} />
        </Field>
        <SubmitButton busy={busy}>Verify code</SubmitButton>
      </form>
      <div className="auth-links">
        <button type="button" className="link-btn" onClick={() => { setRecovery((r) => !r); setCode(''); setError(null); }}>
          {recovery ? 'Use the authenticator app instead' : 'Use a recovery code'}
        </button>
        <button type="button" className="link-btn" onClick={() => setStatus('signed-out')}>
          Sign in as someone else
        </button>
      </div>
    </Card>
  );
}

function Enrol() {
  const { finishSetup, setStatus } = useAuth();
  const [setup, setSetup] = useState(null);
  const [qr, setQr] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [codes, setCodes] = useState(null);
  const [saved, setSaved] = useState(false);
  const [savedErr, setSavedErr] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    auth
      .mfaSetup()
      .then(async (s) => {
        setSetup(s);
        setQr(await QRCode.toDataURL(s.otpauth_uri, { margin: 1, width: 176, color: { dark: '#16202a', light: '#ffffff' } }));
      })
      .catch((err) => (err.code === 'CMS_UNAUTHENTICATED' ? setStatus('signed-out') : setError(`${err.message} ${err.fix}`)));
  }, [setStatus]);

  async function confirm(e) {
    e.preventDefault();
    if (code.length !== 6) {
      setError('Enter the 6-digit code the app shows for CRTDH CMS.');
      return ref.current?.focus();
    }
    setBusy(true);
    setError(null);
    try {
      const res = await auth.mfaConfirm(code);
      setCodes(res.recovery_codes);
    } catch (err) {
      setError(`${err.message} ${err.fix}`);
      setCode('');
      ref.current?.focus();
    } finally {
      setBusy(false);
    }
  }

  if (codes) {
    const text = codes.join('\n');
    return (
      <Card title="Save your recovery codes" lead="If you lose your phone, each of these codes lets you sign in once. Keep them somewhere safe, away from this computer.">
        <ol className="recovery-codes" aria-label="Recovery codes">
          {codes.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ol>
        <div className="row-actions">
          <button type="button" className="btn" onClick={() => navigator.clipboard?.writeText(text)}>
            Copy codes
          </button>
          <a className="btn" download="crtdh-cms-recovery-codes.txt" href={`data:text/plain;charset=utf-8,${encodeURIComponent(`CRTDH CMS recovery codes\n\n${text}\n`)}`}>
            Download codes
          </a>
        </div>
        <label className={`check${savedErr && !saved ? ' has-error' : ''}`}>
          <input type="checkbox" checked={saved} onChange={(e) => { setSaved(e.target.checked); setSavedErr(false); }} />
          <span>I’ve saved these codes</span>
        </label>
        {savedErr && !saved ? (
          <p className="field-error" role="alert">
            Tick the box once the codes are saved. They won’t be shown again.
          </p>
        ) : null}
        <button type="button" className="btn btn-primary btn-block" onClick={() => (saved ? finishSetup() : setSavedErr(true))}>
          Open the editor
        </button>
      </Card>
    );
  }

  return (
    <Card title="Set up two-step sign-in" lead="Every sign-in needs a code from an authenticator app on your phone, such as Google Authenticator or Microsoft Authenticator.">
      <ol className="enrol-steps">
        <li>
          <p>Scan this code with the app.</p>
          <div className="qr-box">{qr ? <img src={qr} width="176" height="176" alt="QR code for adding CRTDH CMS to an authenticator app" /> : <div className="skel" style={{ width: 176, height: 176 }} />}</div>
          {setup ? (
            <p className="field-hint">
              Can’t scan? Type this key into the app: <span className="secret">{setup.secret.replace(/(.{4})/g, '$1 ').trim()}</span>
            </p>
          ) : null}
        </li>
        <li>
          <form onSubmit={confirm} noValidate>
            <Field label="Code from the app" htmlFor="enrol-code" error={error}>
              <CodeInput id="enrol-code" value={code} onChange={(v) => { setCode(v); setError(null); }} error={error} inputRef={ref} />
            </Field>
            <SubmitButton busy={busy}>Confirm code</SubmitButton>
          </form>
        </li>
      </ol>
    </Card>
  );
}

export default function AuthScreens() {
  const { status } = useAuth();
  if (status === 'mfa') return <Mfa />;
  if (status === 'setup') return <Enrol />;
  return <SignIn expired={status === 'expired'} />;
}
