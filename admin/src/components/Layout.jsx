import { useState, useEffect, useRef, useCallback } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  LogOut,
  Mail,
  Search,
  Settings,
  Menu,
  X,
  Home,
  Info,
  Users,
  Image as ImageIcon,
  Lightbulb,
  Wrench,
  Briefcase,
  Building2,
  Video,
  Megaphone,
  ExternalLink,
  FolderOpen,
  Package,
  Link2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { PUBLIC_SITE_URL } from '../api/client';
import AdminSearchModal from './AdminSearchModal';

export default function Layout() {
  const { user, logout } = useAuth();
  const [searchOpen, setSearchOpen] = useState(false);
  // Mobile/tablet navigation drawer (< 900px). On wider screens the sidebar is always visible.
  const [navOpen, setNavOpen] = useState(false);
  const menuButtonRef = useRef(null);
  const sidebarRef = useRef(null);

  const closeNav = useCallback((returnFocus = true) => {
    setNavOpen(false);
    if (returnFocus) menuButtonRef.current?.focus();
  }, []);

  // While the drawer is open: Escape closes it, focus moves into it, and the page behind doesn't scroll.
  useEffect(() => {
    if (!navOpen) return undefined;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        closeNav();
        return;
      }
      // Keep Tab focus inside the open drawer.
      if (e.key === 'Tab' && sidebarRef.current) {
        const items = sidebarRef.current.querySelectorAll('a[href], button:not([disabled])');
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    sidebarRef.current?.querySelector('a, button')?.focus();
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = prevOverflow;
    };
  }, [navOpen, closeNav]);

  // Following a link inside the drawer closes it (no effect on the desktop sidebar).
  const handleNavClick = (e) => {
    if (navOpen && e.target.closest('a')) closeNav(false);
  };

  // Cmd+K or Ctrl+K shortcut key listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className={`app-shell${navOpen ? ' nav-open' : ''}`}>
      <aside
        className="sidebar"
        id="admin-sidebar"
        ref={sidebarRef}
        aria-label="Admin navigation"
      >
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <img className="sidebar-mark" src="/crtdh-favicon.svg" alt="" width="34" height="34" />
            <div>
              <span className="sidebar-logo">CRTDH CMS</span>
              <span className="sidebar-subtitle">Website Management</span>
            </div>
          </div>
          <button
            type="button"
            className="sidebar-close"
            onClick={() => closeNav()}
            aria-label="Close navigation menu"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <nav className="sidebar-nav" onClick={handleNavClick}>
          <NavLink to="/" end className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <LayoutDashboard size={17} className="nav-icon" />
            Dashboard
          </NavLink>

          {/* WEBSITE PAGES GROUP */}
          <div className="sidebar-group-heading">WEBSITE PAGES</div>

          <NavLink to="/home-page" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Home size={17} className="nav-icon" />
            Home Page
          </NavLink>

          <NavLink to="/about-page" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Info size={17} className="nav-icon" />
            About Page
          </NavLink>

          <NavLink to="/team-manager" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Users size={17} className="nav-icon" />
            Team Members
          </NavLink>

          <NavLink to="/resources/innovations" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Lightbulb size={17} className="nav-icon" />
            Innovations
          </NavLink>

          <NavLink to="/resources/products" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Package size={17} className="nav-icon" />
            Products Page
          </NavLink>

          <NavLink to="/resources/equipment" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Wrench size={17} className="nav-icon" />
            Facilities & Equipment
          </NavLink>

          <NavLink to="/resources/services" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Briefcase size={17} className="nav-icon" />
            Services
          </NavLink>

          <NavLink to="/resources/enterprises" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Building2 size={17} className="nav-icon" />
            Enterprises
          </NavLink>

          <NavLink to="/media-gallery" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <ImageIcon size={17} className="nav-icon" />
            Media & Gallery
          </NavLink>

          {/* CONTENT MANAGERS GROUP */}
          <div className="sidebar-group-heading mt-4">CONTENT MANAGERS</div>

          <NavLink to="/hero-manager" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <ImageIcon size={17} className="nav-icon" />
            Hero Carousel
          </NavLink>

          <NavLink to="/resources/news-items" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Megaphone size={17} className="nav-icon" />
            News & Ticker
          </NavLink>

          <NavLink to="/resources/video-blocks" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Video size={17} className="nav-icon" />
            Videos
          </NavLink>

          <NavLink to="/media-library" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <FolderOpen size={17} className="nav-icon" />
            Central Media Library
          </NavLink>

          {/* SETTINGS & SYSTEM GROUP */}
          <div className="sidebar-group-heading mt-4">SETTINGS & SYSTEM</div>

          <NavLink to="/site-settings" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Settings size={17} className="nav-icon" />
            Site Information
          </NavLink>

          <NavLink to="/resources/nav-items" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Link2 size={17} className="nav-icon" />
            Navbar Menu Links
          </NavLink>

          <NavLink to="/contact-messages" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Mail size={17} className="nav-icon" />
            Contact Messages
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <span className="sidebar-avatar" aria-hidden="true">
              {user?.username?.[0]?.toUpperCase() || 'A'}
            </span>
            <div className="sidebar-user-info">
              <span className="sidebar-user-name">{user?.username || 'Administrator'}</span>
              <span className="sidebar-user-role">Superuser</span>
            </div>
          </div>
          <button type="button" onClick={logout} className="sidebar-logout" title="Sign out" aria-label="Sign out">
            <LogOut size={16} aria-hidden="true" />
          </button>
        </div>
      </aside>

      {navOpen && <div className="sidebar-backdrop" onClick={() => closeNav()} aria-hidden="true" />}

      <main className="main-content">
        <header className="top-header">
          <div className="header-left">
            <button
              type="button"
              ref={menuButtonRef}
              className="menu-toggle-btn"
              onClick={() => (navOpen ? closeNav() : setNavOpen(true))}
              aria-label={navOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={navOpen}
              aria-controls="admin-sidebar"
            >
              <Menu size={20} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="search-trigger-btn"
              onClick={() => setSearchOpen(true)}
              aria-label="Search content"
            >
              <Search size={15} aria-hidden="true" />
              <span className="search-trigger-label">Search content…</span>
              <kbd aria-hidden="true">⌘K</kbd>
            </button>
          </div>
          <div className="header-right">
            <a
              href={PUBLIC_SITE_URL}
              target="_blank"
              rel="noreferrer"
              className="btn btn--outline-light btn--sm"
              aria-label="View public website (opens in a new tab)"
            >
              <ExternalLink size={14} aria-hidden="true" />
              <span className="header-link-label">View Public Website</span>
            </a>
          </div>
        </header>

        <div className="page-workspace">
          <Outlet />
        </div>
      </main>

      <AdminSearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
}
