import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Lightbulb,
  Building2,
  Users,
  Calendar,
  Image as ImageIcon,
  Video,
  Megaphone,
  Plus,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';
import { fetchList, PUBLIC_SITE_URL } from '../api/client';

export default function DashboardPage() {
  const [counts, setCounts] = useState({
    slides: 0,
    team: 0,
    gallery: 0,
    videos: 0,
    news: 0,
    innovations: 0,
    enterprises: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      fetchList('/hero-slides/'),
      fetchList('/team-members/'),
      fetchList('/media-events/'),
      fetchList('/video-blocks/'),
      fetchList('/news-items/'),
      fetchList('/innovations/'),
      fetchList('/enterprises/'),
    ]).then(([slides, team, gallery, videos, news, innov, ent]) => {
      setCounts({
        slides: slides.status === 'fulfilled' && Array.isArray(slides.value) ? slides.value.length : 0,
        team: team.status === 'fulfilled' && Array.isArray(team.value) ? team.value.length : 0,
        gallery: gallery.status === 'fulfilled' && Array.isArray(gallery.value) ? gallery.value.length : 0,
        videos: videos.status === 'fulfilled' && Array.isArray(videos.value) ? videos.value.length : 0,
        news: news.status === 'fulfilled' && Array.isArray(news.value) ? news.value.length : 0,
        innovations: innov.status === 'fulfilled' && Array.isArray(innov.value) ? innov.value.length : 13,
        enterprises: ent.status === 'fulfilled' && Array.isArray(ent.value) ? ent.value.length : 28,
      });
      setLoading(false);
    });
  }, []);

  return (
    <div className="dashboard-page">
      <div className="dashboard-hero-banner">
        <div>
          <span className="banner-badge">
            <ShieldCheck size={14} /> CRTDH CMS · Purpose Built
          </span>
          <h1 className="banner-title">Welcome to CRTDH Website Management</h1>
          <p className="banner-desc">
            Directly manage content, visual carousels, research team members, media events, and site settings.
          </p>
        </div>
        <div className="banner-actions">
          <a
            href={PUBLIC_SITE_URL}
            target="_blank"
            rel="noreferrer"
            className="btn btn--outline-light"
          >
            <ExternalLink size={16} /> View Live Public Site
          </a>
        </div>
      </div>

      {/* Public Impact Stats Strip */}
      <div className="dashboard-section">
        <h3 className="section-label">PUBLIC WEBSITE HIGHLIGHT STATS</h3>
        <div className="stats-cards-grid">
          <div className="stat-metric-card">
            <div className="stat-icon-wrap"><Lightbulb size={24} /></div>
            <div>
              <span className="stat-num">{counts.innovations || '13'}+</span>
              <span className="stat-name">Innovations Developed</span>
            </div>
          </div>
          <div className="stat-metric-card">
            <div className="stat-icon-wrap"><Building2 size={24} /></div>
            <div>
              <span className="stat-num">{counts.enterprises || '28'}+</span>
              <span className="stat-name">Enterprises Incubated</span>
            </div>
          </div>
          <div className="stat-metric-card">
            <div className="stat-icon-wrap"><Users size={24} /></div>
            <div>
              <span className="stat-num">{counts.team || '9'}+</span>
              <span className="stat-name">Researchers & Staff</span>
            </div>
          </div>
          <div className="stat-metric-card">
            <div className="stat-icon-wrap"><Calendar size={24} /></div>
            <div>
              <span className="stat-num">8+</span>
              <span className="stat-name">Years Sponsored by DSIR</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Content Launchers */}
      <div className="dashboard-section mt-8">
        <h3 className="section-label">QUICK ACTIONS</h3>
        <div className="quick-actions-grid">
          <Link to="/hero-manager" className="quick-action-card">
            <div className="quick-action-icon"><ImageIcon size={20} /></div>
            <div className="quick-action-info">
              <h4>Add Hero Slide</h4>
              <p>Customize banner heading & slide image</p>
            </div>
            <Plus size={18} className="action-plus" />
          </Link>

          <Link to="/team-manager" className="quick-action-card">
            <div className="quick-action-icon"><Users size={20} /></div>
            <div className="quick-action-info">
              <h4>Add Team Member</h4>
              <p>Add faculty, PI, or staff profile</p>
            </div>
            <Plus size={18} className="action-plus" />
          </Link>

          <Link to="/media-gallery" className="quick-action-card">
            <div className="quick-action-icon"><ImageIcon size={20} /></div>
            <div className="quick-action-info">
              <h4>Create Gallery Event</h4>
              <p>Bulk upload workshop or camp photos</p>
            </div>
            <Plus size={18} className="action-plus" />
          </Link>

          <Link to="/resources/news-items" className="quick-action-card">
            <div className="quick-action-icon"><Megaphone size={20} /></div>
            <div className="quick-action-info">
              <h4>Add News Ticker Item</h4>
              <p>Publish current announcements</p>
            </div>
            <Plus size={18} className="action-plus" />
          </Link>
        </div>
      </div>

      {/* Active Content Inventories */}
      <div className="dashboard-section mt-8">
        <h3 className="section-label">CONTENT INVENTORY SUMMARY</h3>
        <div className="inventory-cards-grid">
          <div className="inventory-card">
            <div className="inv-header">
              <ImageIcon size={20} />
              <span>Hero Slides</span>
            </div>
            <div className="inv-count">{counts.slides}</div>
            <Link to="/hero-manager" className="inv-link">
              Manage Slides &rarr;
            </Link>
          </div>

          <div className="inventory-card">
            <div className="inv-header">
              <Users size={20} />
              <span>Team Members</span>
            </div>
            <div className="inv-count">{counts.team}</div>
            <Link to="/team-manager" className="inv-link">
              Manage Team &rarr;
            </Link>
          </div>

          <div className="inventory-card">
            <div className="inv-header">
              <ImageIcon size={20} />
              <span>Gallery Events</span>
            </div>
            <div className="inv-count">{counts.gallery}</div>
            <Link to="/media-gallery" className="inv-link">
              Manage Gallery &rarr;
            </Link>
          </div>

          <div className="inventory-card">
            <div className="inv-header">
              <Megaphone size={20} />
              <span>News Items</span>
            </div>
            <div className="inv-count">{counts.news}</div>
            <Link to="/resources/news-items" className="inv-link">
              Manage News &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
