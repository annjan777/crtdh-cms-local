import { useMemo, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, LogOut, Mail, Search, Settings, ChevronDown, Home, Info } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { groupedSchemas } from '../resources/schemas';
import { getIcon } from '../resources/icons';

export default function Layout() {
  const { user, logout } = useAuth();
  const groups = groupedSchemas();
  const [query, setQuery] = useState('');
  const [collapsed, setCollapsed] = useState({});

  const q = query.trim().toLowerCase();
  const filteredGroups = useMemo(() => {
    if (!q) return groups;
    return groups
      .map((g) => ({ ...g, items: g.items.filter((item) => item.label.toLowerCase().includes(q)) }))
      .filter((g) => g.items.length > 0);
  }, [groups, q]);

  const initials = (user?.username || '?').slice(0, 2).toUpperCase();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <span className="sidebar-mark" aria-hidden="true">
              C
            </span>
            <div>
              <span className="sidebar-logo">CRTDH</span>
              <span className="sidebar-subtitle">Content Admin</span>
            </div>
          </div>
        </div>

        <div className="sidebar-search">
          <Search size={15} aria-hidden="true" />
          <input
            type="search"
            placeholder="Jump to a section…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search sections"
          />
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <LayoutDashboard size={17} className="nav-icon" aria-hidden="true" />
            Dashboard
          </NavLink>
          <NavLink to="/home-page" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Home size={17} className="nav-icon" aria-hidden="true" />
            Home Page
          </NavLink>
          <NavLink to="/about-page" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Info size={17} className="nav-icon" aria-hidden="true" />
            About Page
          </NavLink>
          <NavLink to="/site-settings" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Settings size={17} className="nav-icon" aria-hidden="true" />
            Site Settings
          </NavLink>
          <NavLink to="/contact-messages" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Mail size={17} className="nav-icon" aria-hidden="true" />
            Contact Messages
          </NavLink>

          <div className="sidebar-divider" role="separator" />

          {filteredGroups.map(({ group, icon, items }) => {
            const GroupIcon = getIcon(icon);
            const isCollapsed = !!collapsed[group] && !q;
            return (
              <div className="sidebar-group" key={group}>
                <button
                  type="button"
                  className="sidebar-group-label"
                  onClick={() => setCollapsed((prev) => ({ ...prev, [group]: !prev[group] }))}
                  aria-expanded={!isCollapsed}
                >
                  <GroupIcon size={13} aria-hidden="true" />
                  <span>{group}</span>
                  <ChevronDown size={13} className={`sidebar-group-chevron${isCollapsed ? ' is-collapsed' : ''}`} aria-hidden="true" />
                </button>
                {!isCollapsed && (
                  <div className="sidebar-group-items">
                    {items.map((schema) => {
                      const ItemIcon = getIcon(schema.icon);
                      return (
                        <NavLink
                          key={schema.key}
                          to={`/resources/${schema.key}`}
                          className={({ isActive }) => `sidebar-link sidebar-link-sub${isActive ? ' active' : ''}`}
                        >
                          <ItemIcon size={16} className="nav-icon" aria-hidden="true" />
                          {schema.label}
                        </NavLink>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}

          {q && filteredGroups.length === 0 && <p className="sidebar-empty">No sections match “{query}”.</p>}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <span className="sidebar-avatar" aria-hidden="true">
              {initials}
            </span>
            <div className="sidebar-user-info">
              <span className="sidebar-user-name">{user?.username}</span>
              <span className="sidebar-user-role">Administrator</span>
            </div>
          </div>
          <button type="button" className="sidebar-logout" onClick={logout} title="Log out">
            <LogOut size={16} aria-hidden="true" />
          </button>
        </div>
      </aside>

      <div className="main-column">
        <main className="content-area">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
