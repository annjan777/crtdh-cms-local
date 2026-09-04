import { ArrowRight, User } from 'lucide-react';

export default function LivePreviewPane({ type, data }) {
  if (type === 'hero') {
    const {
      eyebrow,
      heading,
      highlight_heading,
      heading_end,
      description,
      primary_button_label,
      primary_button_link,
      secondary_button_label,
      secondary_button_link,
      image,
      image_preview,
    } = data || {};

    const bgUrl = typeof image === 'string' ? image : (image_preview || (image instanceof File ? URL.createObjectURL(image) : ''));

    return (
      <div className="live-preview-box live-preview-box--hero">
        <div className="preview-header">
          <span className="preview-tag">LIVE WEBSITE PREVIEW</span>
          <span className="preview-sub">Hero Slide Component</span>
        </div>
        <div
          className="preview-hero-frame"
          style={{
            backgroundImage: bgUrl ? `linear-gradient(90deg, rgba(15,76,117,0.92) 35%, rgba(15,76,117,0.4) 100%), url(${bgUrl})` : undefined,
          }}
        >
          <div className="preview-hero-inner">
            <span className="preview-hero-eyebrow">{eyebrow || 'DSIR · GOVERNMENT OF INDIA'}</span>
            <h1 className="preview-hero-title">
              {heading || 'Common Research &'}{' '}
              <span className="preview-hero-highlight">{highlight_heading || 'Technology Development'}</span>{' '}
              {heading_end !== undefined ? heading_end : 'Hub'}
            </h1>
            <p className="preview-hero-desc">
              {description || 'Building affordable healthcare technology for a billion people, at IIT Kharagpur.'}
            </p>
            <div className="preview-hero-actions">
              <span className="preview-btn preview-btn--accent">
                {primary_button_label || 'Explore Innovations'}
                <ArrowRight size={14} />
              </span>
              <span className="preview-btn preview-btn--ghost">
                {secondary_button_label || 'About CRTDH'}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (type === 'team') {
    const { name, category_name, photo, designation, institution } = data || {};
    return (
      <div className="live-preview-box">
        <div className="preview-header">
          <span className="preview-tag">LIVE WEBSITE PREVIEW</span>
          <span className="preview-sub">Team Card Component</span>
        </div>
        <div className="preview-team-card">
          <div className="preview-team-avatar">
            {photo ? (
              <img src={photo} alt={name} />
            ) : (
              <div className="preview-team-avatar-fallback">
                <User size={32} />
              </div>
            )}
          </div>
          <div className="preview-team-info">
            <h3 className="preview-team-name">{name || 'Person Name'}</h3>
            <span className="preview-team-cat">{category_name || designation || 'Team Category'}</span>
            {institution && <span className="preview-team-inst">{institution}</span>}
          </div>
        </div>
      </div>
    );
  }

  if (type === 'about') {
    const { intro, mission_vision, focus_intro, ecosystem_heading, ecosystem_image, pi_desk_image, dsir_about, iitkgp_about } = data || {};
    return (
      <div className="live-preview-box">
        <div className="preview-header">
          <span className="preview-tag">LIVE WEBSITE PREVIEW</span>
          <span className="preview-sub">About Page Content</span>
        </div>
        <div className="preview-about-frame">
          <div className="preview-about-section">
            <h4>About CRTDH Intro</h4>
            <p className="preview-prose">{intro || 'Innovation plays a critical role in shaping...'}</p>
          </div>
          {mission_vision && (
            <div className="preview-about-section">
              <h4>Mission & Vision</h4>
              <p className="preview-prose">{mission_vision}</p>
            </div>
          )}
          {ecosystem_heading && (
            <div className="preview-about-section">
              <h4>{ecosystem_heading}</h4>
              {ecosystem_image && <img src={typeof ecosystem_image === 'string' ? ecosystem_image : URL.createObjectURL(ecosystem_image)} alt="Ecosystem" className="preview-media" />}
            </div>
          )}
          {pi_desk_image && (
            <div className="preview-about-section">
              <h4>PI's Desk Photo</h4>
              <img src={typeof pi_desk_image === 'string' ? pi_desk_image : URL.createObjectURL(pi_desk_image)} alt="PI Desk" className="preview-media" />
            </div>
          )}
        </div>
      </div>
    );
  }

  if (type === 'site-settings') {
    const { address, phone_primary, email_primary, facebook_url, linkedin_url, twitter_url, instagram_url, map_embed_url } = data || {};
    return (
      <div className="live-preview-box">
        <div className="preview-header">
          <span className="preview-tag">LIVE WEBSITE PREVIEW</span>
          <span className="preview-sub">Header & Footer Contact Cards</span>
        </div>
        <div className="preview-settings-frame">
          <div className="preview-contact-card">
            <h4>Public Contact Details</h4>
            <p className="preview-address">📍 {address || 'IIT Kharagpur, West Midnapur'}</p>
            <p className="preview-phone">📞 {phone_primary || '+91-88200 51894'}</p>
            <p className="preview-email">✉️ {email_primary || 'suman@mech.iitkgp.ac.in'}</p>
          </div>
          {map_embed_url && (
            <div className="preview-map-box mt-4">
              <h4>Map Embed Location</h4>
              <span className="preview-map-url">{map_embed_url}</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="live-preview-box">
      <div className="preview-header">
        <span className="preview-tag">LIVE WEBSITE PREVIEW</span>
      </div>
      <div className="preview-fallback-content">
        <p>Live preview active for website content editing.</p>
      </div>
    </div>
  );
}
