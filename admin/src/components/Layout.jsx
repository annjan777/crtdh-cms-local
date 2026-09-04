import { useState, useEffect } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  LogOut,
  Mail,
  Search,
  Settings,
  ChevronDown,
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
  Shield,
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
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <span className="sidebar-mark">CR</span>
            <div>
              <span className="sidebar-logo">CRTDH CMS</span>
              <span className="sidebar-subtitle">Website Management</span>
            </div>
          </div>
        </div>

        {/* Global Search Bar */}
        <div className="sidebar-search" onClick={() => setSearchOpen(true)}>
          <Search size={14} />
          <span className="search-placeholder">Search website...</span>
          <kbd className="search-kbd">⌘K</kbd>
        </div>

        <nav className="sidebar-nav">
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
            <span className="user-avatar">{user?.username?.[0]?.toUpperCase() || 'A'}</span>
            <div className="user-details">
              <span className="user-name">{user?.username || 'Administrator'}</span>
              <span className="user-role">Superuser</span>
            </div>
          </div>
          <button onClick={logout} className="logout-btn" title="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="top-header">
          <div className="header-left">
            <button className="search-trigger-btn" onClick={() => setSearchOpen(true)}>
              <Search size={15} />
              <span>Search across website content (Cmd+K)...</span>
              <kbd>⌘K</kbd>
            </button>
          </div>
          <div className="header-right">
            <a
              href={PUBLIC_SITE_URL}
              target="_blank"
              rel="noreferrer"
              className="btn btn--outline-light btn--sm"
            >
              <ExternalLink size={14} /> View Public Website
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
