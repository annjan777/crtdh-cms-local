import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Mail, Settings, Home, Info } from 'lucide-react';
import { groupedSchemas } from '../resources/schemas';
import { getIcon } from '../resources/icons';
import { countResource } from '../api/resources';
import { SkeletonCards } from '../components/Skeleton';
import apiClient from '../api/client';

// A handful of headline resources worth a stat tile on the landing page —
// deliberately a subset (not all ~25), chosen for the numbers staff care
// about at a glance.
const HEADLINE_STATS = [
  { key: 'team-members', label: 'Team Members', endpoint: '/team-members/', icon: 'users' },
  { key: 'innovations', label: 'Innovations', endpoint: '/innovations/', icon: 'lightbulb' },
  { key: 'enterprises', label: 'Enterprises', endpoint: '/enterprises/', icon: 'building' },
  { key: 'equipment', label: 'Equipment', endpoint: '/equipment/', icon: 'wrench' },
  { key: 'media-events', label: 'Media Events', endpoint: '/media-events/', icon: 'calendar' },
  { key: 'documents', label: 'Documents', endpoint: '/documents/', icon: 'file' },
];

export default function DashboardPage() {
  const groups = groupedSchemas();
  const [stats, setStats] = useState(null);
  const [recentMessages, setRecentMessages] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all(HEADLINE_STATS.map((s) => countResource(s.endpoint).catch(() => 0))).then((counts) => {
      if (!cancelled) setStats(counts);
    });
    apiClient
      .get('/contact-messages/', { params: { page_size: 4 } })
      .then(({ data }) => {
        if (!cancelled) setRecentMessages(Array.isArray(data) ? data : data.results || []);
      })
      .catch(() => {
        if (!cancelled) setRecentMessages([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="page-lead">Every editable section of the CRTDH site lives here — pick a card to view, add, edit, reorder, or delete content.</p>
        </div>
      </div>

      {stats === null ? (
        <SkeletonCards count={HEADLINE_STATS.length} />
      ) : (
        <div className="stat-grid">
          {HEADLINE_STATS.map((s, i) => {
            const Icon = getIcon(s.icon);
            return (
              <Link to={`/resources/${s.key}`} className="stat-card" key={s.key}>
                <span className="stat-card-icon">
                  <Icon size={18} aria-hidden="true" />
                </span>
                <span className="stat-card-value">{stats[i]}</span>
                <span className="stat-card-label">{s.label}</span>
              </Link>
            );
          })}
        </div>
      )}

      <div className="dash-quicklinks">
        <Link to="/home-page" className="dash-card dash-card-highlight">
          <span className="dash-card-icon">
            <Home size={18} aria-hidden="true" />
          </span>
          <span className="dash-card-body">
            <span className="dash-card-title">Home Page</span>
            <span className="dash-card-desc">Objective, Enterprises Engagement, Women Empowerment, Location & Facility, Membership (singleton)</span>
          </span>
          <ArrowRight size={16} className="dash-card-arrow" aria-hidden="true" />
        </Link>
        <Link to="/about-page" className="dash-card dash-card-highlight">
          <span className="dash-card-icon">
            <Info size={18} aria-hidden="true" />
          </span>
          <span className="dash-card-body">
            <span className="dash-card-title">About Page</span>
            <span className="dash-card-desc">Intro, mission & vision, ecosystem and PI's desk content (singleton)</span>
          </span>
          <ArrowRight size={16} className="dash-card-arrow" aria-hidden="true" />
        </Link>
        <Link to="/site-settings" className="dash-card dash-card-highlight">
          <span className="dash-card-icon">
            <Settings size={18} aria-hidden="true" />
          </span>
          <span className="dash-card-body">
            <span className="dash-card-title">Site Settings</span>
            <span className="dash-card-desc">Contact details, map, social links (singleton)</span>
          </span>
          <ArrowRight size={16} className="dash-card-arrow" aria-hidden="true" />
        </Link>
        <Link to="/contact-messages" className="dash-card dash-card-highlight">
          <span className="dash-card-icon">
            <Mail size={18} aria-hidden="true" />
          </span>
          <span className="dash-card-body">
            <span className="dash-card-title">Contact Messages</span>
            <span className="dash-card-desc">
              {recentMessages === null ? 'Loading…' : `${recentMessages.length > 0 ? 'Recent' : 'No'} submissions from the public contact form`}
            </span>
          </span>
          <ArrowRight size={16} className="dash-card-arrow" aria-hidden="true" />
        </Link>
      </div>

      {recentMessages && recentMessages.length > 0 && (
        <section className="dash-section">
          <h2>Recent contact messages</h2>
          <div className="recent-messages">
            {recentMessages.slice(0, 4).map((m) => (
              <Link to="/contact-messages" className="recent-message" key={m.id}>
                <span className="recent-message-name">{m.name}</span>
                <span className="recent-message-text">{m.message}</span>
                <span className="recent-message-date">
                  {m.created_at ? new Date(m.created_at).toLocaleDateString() : ''}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {groups.map(({ group, icon, items }) => {
        const GroupIcon = getIcon(icon);
        return (
          <section key={group} className="dash-section">
            <h2>
              <GroupIcon size={14} aria-hidden="true" />
              {group}
            </h2>
            <div className="card-grid">
              {items.map((schema) => {
                const Icon = getIcon(schema.icon);
                return (
                  <Link key={schema.key} to={`/resources/${schema.key}`} className="dash-card">
                    <span className="dash-card-icon">
                      <Icon size={18} aria-hidden="true" />
                    </span>
                    <span className="dash-card-body">
                      <span className="dash-card-title">{schema.label}</span>
                      {schema.children && (
                        <span className="dash-card-desc">incl. {schema.children.map((c) => c.label).join(', ')}</span>
                      )}
                    </span>
                    <ArrowRight size={16} className="dash-card-arrow" aria-hidden="true" />
                  </Link>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
