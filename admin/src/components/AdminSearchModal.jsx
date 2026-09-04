import { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, Layers, Users, Image, Lightbulb, Wrench, Settings, ArrowRight, Globe } from 'lucide-react';
import { fetchList } from '../api/client';

export default function AdminSearchModal({ isOpen, onClose }) {
  const [query, setQuery] = useState('');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setLoading(true);

      Promise.allSettled([
        fetchList('/team-members/'),
        fetchList('/hero-slides/'),
        fetchList('/media-events/'),
        fetchList('/innovations/'),
        fetchList('/equipment/'),
      ]).then(([teamRes, slidesRes, eventsRes, innovRes, equipRes]) => {
        const aggregated = [];

        // Static website pages
        const pages = [
          { title: 'Home Page Sections', type: 'Page', icon: Globe, path: '/home-page' },
          { title: 'About Page Content', type: 'Page', icon: Globe, path: '/about-page' },
          { title: 'Team Members Manager', type: 'Page', icon: Users, path: '/team-manager' },
          { title: 'Innovations Directory', type: 'Page', icon: Lightbulb, path: '/resources/innovations' },
          { title: 'Facilities & Equipment', type: 'Page', icon: Wrench, path: '/resources/equipment' },
          { title: 'Services List', type: 'Page', icon: Layers, path: '/resources/services' },
          { title: 'Enterprises Incubated', type: 'Page', icon: Layers, path: '/resources/enterprises' },
          { title: 'Media & Gallery Manager', type: 'Page', icon: Image, path: '/media-gallery' },
          { title: 'Hero Carousel Manager', type: 'Page', icon: Image, path: '/hero-manager' },
          { title: 'Central Media Library', type: 'Page', icon: Image, path: '/media-library' },
          { title: 'Site Settings & Branding', type: 'Page', icon: Settings, path: '/site-settings' },
        ];
        pages.forEach((p) => aggregated.push(p));

        if (teamRes.status === 'fulfilled' && Array.isArray(teamRes.value)) {
          teamRes.value.forEach((m) => {
            aggregated.push({
              title: m.name,
              subtitle: m.category_name || 'Team Member',
              type: 'Team Member',
              icon: Users,
              path: '/team-manager',
            });
          });
        }

        if (slidesRes.status === 'fulfilled' && Array.isArray(slidesRes.value)) {
          slidesRes.value.forEach((s) => {
            aggregated.push({
              title: s.heading || `Hero Slide ${s.id}`,
              subtitle: s.highlight_heading || s.eyebrow || 'Hero Carousel',
              type: 'Hero Slide',
              icon: Image,
              path: '/hero-manager',
            });
          });
        }

        if (eventsRes.status === 'fulfilled' && Array.isArray(eventsRes.value)) {
          eventsRes.value.forEach((e) => {
            aggregated.push({
              title: e.title,
              subtitle: 'Gallery Event',
              type: 'Media Event',
              icon: Image,
              path: '/media-gallery',
            });
          });
        }

        if (innovRes.status === 'fulfilled' && Array.isArray(innovRes.value)) {
          innovRes.value.forEach((inv) => {
            aggregated.push({
              title: inv.title,
              subtitle: 'Innovation Record',
              type: 'Innovation',
              icon: Lightbulb,
              path: `/resources/innovations/${inv.id}`,
            });
          });
        }

        if (equipRes.status === 'fulfilled' && Array.isArray(equipRes.value)) {
          equipRes.value.forEach((eq) => {
            aggregated.push({
              title: eq.name,
              subtitle: 'Facility Equipment',
              type: 'Equipment',
              icon: Wrench,
              path: `/resources/equipment/${eq.id}`,
            });
          });
        }

        setItems(aggregated);
        setLoading(false);
      });
    } else {
      setQuery('');
    }
  }, [isOpen]);

  const filtered = useMemo(() => {
    if (!query.trim()) return items.slice(0, 10);
    const q = query.toLowerCase();
    return items.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        (item.subtitle && item.subtitle.toLowerCase().includes(q)) ||
        item.type.toLowerCase().includes(q)
    );
  }, [query, items]);

  if (!isOpen) return null;

  const handleSelect = (path) => {
    onClose();
    navigate(path);
  };

  return (
    <div className="search-modal-backdrop" onClick={onClose}>
      <div className="search-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="search-modal-header">
          <Search size={18} className="search-modal-icon" />
          <input
            ref={inputRef}
            type="text"
            className="search-modal-input"
            placeholder="Search pages, slides, team members, media, settings... (Esc to close)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') onClose();
            }}
          />
          <button className="search-modal-close" onClick={onClose} aria-label="Close search">
            <X size={16} />
          </button>
        </div>

        <div className="search-modal-body">
          {loading ? (
            <div className="search-modal-status">Loading search index...</div>
          ) : filtered.length === 0 ? (
            <div className="search-modal-status">No matching results found for "{query}"</div>
          ) : (
            <ul className="search-modal-results">
              {filtered.map((item, idx) => {
                const IconComponent = item.icon || Globe;
                return (
                  <li
                    key={idx}
                    className="search-modal-item"
                    onClick={() => handleSelect(item.path)}
                  >
                    <div className="search-modal-item-icon">
                      <IconComponent size={16} />
                    </div>
                    <div className="search-modal-item-content">
                      <span className="search-modal-item-title">{item.title}</span>
                      {item.subtitle && <span className="search-modal-item-subtitle">{item.subtitle}</span>}
                    </div>
                    <span className="search-modal-item-badge">{item.type}</span>
                    <ArrowRight size={14} className="search-modal-item-arrow" />
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
