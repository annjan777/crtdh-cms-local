import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useMatch } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { ROLE_LABEL, topRole } from '../auth/roles.js';
import { SITE_PAGE_ID, useChanges } from './ChangesContext.jsx';
import DraftBar from './DraftBar.jsx';
import { USE_MOCK } from '../api/client.js';


function UserMenu() {
  const { user, logout, signOutEverywhere } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => {
      if (e.type === 'keydown' && e.key !== 'Escape') return;
      if (e.type === 'mousedown' && ref.current?.contains(e.target)) return;
      setOpen(false);
      if (e.type === 'keydown') ref.current?.querySelector('button')?.focus();
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, [open]);
  const role = ROLE_LABEL[topRole(user.roles)] || 'Editor';
  return (
    <div className="user-menu" ref={ref}>
      <button type="button" className="user-btn" aria-expanded={open} aria-haspopup="menu" onClick={() => setOpen((o) => !o)}>
        <span className="avatar" aria-hidden="true">
          {user.name?.[0] || user.username[0]}
        </span>
        <span className="user-name">{user.name}</span>
      </button>
      {open ? (
        <div className="menu" role="menu">
          <p className="menu-meta">
            Signed in as {user.username} · {role}
          </p>
          <Link role="menuitem" className="menu-item" to="/claude-access" onClick={() => setOpen(false)}>
            Claude access
          </Link>
          <button type="button" role="menuitem" className="menu-item" onClick={logout}>
            Sign out
          </button>
          <button type="button" role="menuitem" className="menu-item" onClick={signOutEverywhere}>
            Sign out on all devices
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function PageNav({ sections, selectedSection, onSelectSection, onNavigate }) {
  const { pages } = useChanges();
  const { isAdmin, canPublish } = useAuth();
  const match = useMatch('/pages/:pageId');
  const openId = match?.params.pageId;
  const list = pages || [];
  const sitePages = list.filter((p) => p.path);
  const settings = list.find((p) => p.id === SITE_PAGE_ID);
  const item = (p) => (
    <li key={p.id}>
      <NavLink to={`/pages/${p.id}`} className="nav-link" onClick={onNavigate} aria-current={openId === p.id ? 'page' : undefined}>
        <span>{p.title}</span>
        {p.has_changes ? (
          <span className="dot" role="img" aria-label="has unpublished changes" title="" />
        ) : null}
      </NavLink>
      {openId === p.id && sections ? (
        <ol className="section-list" aria-label={`Sections of ${p.title}`}>
          {sections.map((s, i) => (
            <li key={s.id}>
              <button type="button" className="section-link" aria-current={selectedSection === s.id ? 'true' : undefined} onClick={() => onSelectSection(s.id)}>
                <span className="num">{i + 1}</span>
                <span className="section-name">{s.label}</span>
                {s.hint ? <span className="section-hint">{s.hint}</span> : null}
              </button>
            </li>
          ))}
        </ol>
      ) : null}
    </li>
  );
  return (
    <nav className="page-nav" aria-label="Website">
      <h2 className="nav-heading">Pages</h2>
      {pages ? (
        <ul className="nav-list">{sitePages.map(item)}</ul>
      ) : (
        <ul className="nav-list" aria-hidden="true">
          {Array.from({ length: 8 }, (_, i) => (
            <li key={i}>
              <span className="skel skel-line" style={{ width: `${50 + ((i * 17) % 40)}%` }} />
            </li>
          ))}
        </ul>
      )}
      <h2 className="nav-heading">Site</h2>
      <ul className="nav-list">
        {settings ? item(settings) : null}
        <li>
          <NavLink to="/review" className="nav-link" onClick={onNavigate}>
            Review &amp; publish
          </NavLink>
        </li>
        <li>
          <NavLink to="/history" className="nav-link" onClick={onNavigate}>
            Publish history
          </NavLink>
        </li>
        {canPublish ? (
          <li>
            <NavLink to="/messages" className="nav-link" onClick={onNavigate}>
              Messages
            </NavLink>
          </li>
        ) : null}
        <li>
          <NavLink to="/claude-access" className="nav-link" onClick={onNavigate}>
            Claude access
          </NavLink>
        </li>
        {isAdmin ? (
          <li>
            <NavLink to="/users" className="nav-link" onClick={onNavigate}>
              Users
            </NavLink>
          </li>
        ) : null}
      </ul>
    </nav>
  );
}

export default function AppShell({ crumb, children, onOpenNav }) {
  const loc = useLocation();
  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <header className="topbar">
        {onOpenNav ? (
          <button type="button" className="btn nav-toggle" onClick={onOpenNav} aria-label="Open pages menu">
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <path d="M2 4h14M2 9h14M2 14h14" stroke="currentColor" strokeWidth="1.6" fill="none" />
            </svg>
            <span>Pages</span>
          </button>
        ) : null}
        <Link to="/pages/home" className="brand" aria-label="CRTDH website">
          <img src="/apple-touch-icon.png" alt="" width="28" height="28" />
          <span className="brand-name">CRTDH website</span>
        </Link>
        {crumb ? (
          <span className="crumb" key={loc.pathname}>
            <span aria-hidden="true">/</span> {crumb}
          </span>
        ) : null}
        {USE_MOCK ? <span className="mock-flag" title="">Test data</span> : null}
        <DraftBar />
        <UserMenu />
      </header>
      {children}
    </div>
  );
}
