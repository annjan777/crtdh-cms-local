// Stand-in for `frontend/src/site` so the admin builds and its canvas works
// before the frontend lane merges. It renders every registry section from
// snapshot-shaped data in the public site's colours and type, with the
// data-cms-section / data-cms-item attributes the real components will carry.
// Integration replaces it by pointing the `@site` alias at the real package.
import './shim.css';
import { useCmsPreview } from '../cms-context.js';
import { sanitizeRich } from '../sanitize.js';

export const __shim = true;

const strip = (h) => String(h || '').replace(/<[^>]+>/g, '').trim();
const visible = (rows) => (rows || []).filter((r) => r.is_published !== false);

function rowsFor(data, section) {
  const rows = visible(data.collections?.[section.resource]);
  return section.filter ? rows.filter((r) => Object.entries(section.filter).every(([k, v]) => r[k] === v)) : rows;
}

function Hero({ section, data }) {
  const { selected } = useCmsPreview();
  const slides = rowsFor(data, section);
  if (!slides.length) return null;
  const slide = slides.find((s) => selected?.sectionId === section.id && s.id === selected.pk) || slides[0];
  const n = slides.indexOf(slide) + 1;
  return (
    <section className="s-hero" data-cms-section={section.id} data-cms-item={slide.id} data-cms-tag={`${section.label} · slide ${n} of ${slides.length}`}>
      <img className="s-hero-img" src={slide.image} alt={slide.alt_text || ''} style={{ objectPosition: slide.image_position || 'center' }} />
      <div className="s-hero-text">
        {slide.eyebrow ? <p className="s-eyebrow">{slide.eyebrow}</p> : null}
        <h1>
          {slide.heading} {slide.highlight_heading ? <span className="s-hl">{slide.highlight_heading}</span> : null} {slide.heading_end}
        </h1>
        {slide.description ? <p className="s-lead">{slide.description}</p> : null}
        <p className="s-actions">
          {slide.primary_button_label ? <a className="s-btn" href={slide.primary_button_link || '#'}>{slide.primary_button_label}</a> : null}
          {slide.secondary_button_label ? <a className="s-btn s-btn-2" href={slide.secondary_button_link || '#'}>{slide.secondary_button_label}</a> : null}
        </p>
      </div>
      {slides.length > 1 ? (
        <p className="s-dots" aria-hidden="true">
          {slides.slice(0, 8).map((s) => (
            <span key={s.id} className={s === slide ? 'on' : ''} />
          ))}
        </p>
      ) : null}
    </section>
  );
}

function News({ section, data }) {
  const rows = rowsFor(data, section);
  if (!rows.length) return null;
  return (
    <section className="s-news" data-cms-section={section.id} data-cms-tag={section.label}>
      <strong>Latest</strong>
      <ul>
        {rows.map((r) => (
          <li key={r.id} data-cms-item={r.id}>
            {r.text}
          </li>
        ))}
      </ul>
    </section>
  );
}

function firstImage(section, row) {
  const f = section.fields.find((x) => x.type === 'image');
  if (f && row[f.name]) return row[f.name];
  for (const k of ['images', 'items']) if (row[k]?.[0]) return row[k][0].image;
  return null;
}

function titleOf(section, row) {
  return (section.item_label || []).map((n) => strip(row[n])).filter(Boolean).join(' ');
}

function Cards({ section, data }) {
  const rows = rowsFor(data, section);
  if (!rows.length) return null;
  const textField = section.fields.find((f) => ['textarea', 'richtext'].includes(f.type));
  const sub = section.fields.find((f) => f.type === 'text' && !(section.item_label || []).includes(f.name));
  const people = section.resource === 'team-members';
  const links = section.resource === 'media-coverage-links' || section.resource === 'documents' || section.resource === 'nav-items';
  if (links)
    return (
      <section className="s-section" data-cms-section={section.id} data-cms-tag={section.label}>
        <h2>{section.label}</h2>
        <ul className="s-links">
          {rows.map((r) => (
            <li key={r.id} data-cms-item={r.id}>
              <a href={r.url || r.file || '#'}>{titleOf(section, r)}</a>
            </li>
          ))}
        </ul>
      </section>
    );
  if (section.resource === 'objective-rows')
    return (
      <section className="s-section" data-cms-section={section.id} data-cms-tag={section.label}>
        <h2>{section.label}</h2>
        <table className="s-table">
          <thead>
            <tr>
              <th>Stage</th>
              <th>What happens</th>
              <th>Outcome</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} data-cms-item={r.id}>
                <td>{r.category}</td>
                <td>{r.task}</td>
                <td>{r.outcome}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  return (
    <section className={`s-section${section.resource === 'image-grid-blocks' ? ' s-blocks' : ''}`} data-cms-section={section.id} data-cms-tag={section.label}>
      <h2>{section.label}</h2>
      {section.resource === 'image-grid-blocks' ? (
        rows.map((b) => (
          <div key={b.id} className="s-block" data-cms-item={b.id}>
            <h3>{b.section_title}</h3>
            {b.intro ? <p className="s-measure">{b.intro}</p> : null}
            <div className="s-grid">
              {(b.items || []).filter((i) => i.is_published !== false).slice(0, 8).map((i) => (
                <figure key={i.id}>
                  <img src={i.image} alt={i.image_alt || ''} loading="lazy" />
                  {i.caption ? <figcaption>{i.caption}</figcaption> : null}
                </figure>
              ))}
            </div>
          </div>
        ))
      ) : (
        <div className={`s-grid${people ? ' s-people' : ''}`}>
          {rows.map((r) => {
            const src = firstImage(section, r);
            return (
              <article key={r.id} className="s-card" data-cms-item={r.id}>
                {src ? <img src={src} alt="" loading="lazy" /> : section.fields.some((f) => f.type === 'image') ? <div className="s-ph" /> : null}
                <h3>{titleOf(section, r) || strip(r.text)}</h3>
                {sub && r[sub.name] ? <p className="s-meta">{r[sub.name]}</p> : null}
                {r.designation && sub?.name !== 'designation' ? <p className="s-meta">{r.designation}</p> : null}
                {textField && r[textField.name] && !people ? <p className="s-clip">{strip(r[textField.name])}</p> : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function Single({ section, data }) {
  const row = data.singletons?.[section.resource] || {};
  const filled = section.fields.filter((f) => row[f.name]);
  if (!filled.length) return null;
  const heading = section.fields.find((f) => f.type === 'text' && /heading|title|address/.test(f.name) && row[f.name]);
  return (
    <section className="s-section" data-cms-section={section.id} data-cms-tag={section.label}>
      <h2>{heading ? row[heading.name] : section.label}</h2>
      <div className="s-single">
        <div className="s-measure">
          {filled
            .filter((f) => f !== heading)
            .map((f) => {
              if (f.type === 'image') return null;
              if (f.type === 'richtext') return <div key={f.name} className="s-rich" dangerouslySetInnerHTML={{ __html: sanitizeRich(row[f.name]) }} />;
              if (f.type === 'url') return <p key={f.name}><a href={row[f.name]}>{f.label}</a></p>;
              if (f.type === 'text') return <p key={f.name} className="s-meta">{f.label}: {row[f.name]}</p>;
              return <p key={f.name}>{row[f.name]}</p>;
            })}
        </div>
        {filled.some((f) => f.type === 'image') ? (
          <div className="s-figs">
            {filled.filter((f) => f.type === 'image').slice(0, 3).map((f) => (
              <img key={f.name} src={row[f.name]} alt={row[f.alt_field] || ''} loading="lazy" />
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function render(section, data) {
  if (section.id === 'home.hero') return <Hero key={section.id} section={section} data={data} />;
  if (section.id === 'home.news') return <News key={section.id} section={section} data={data} />;
  if (section.kind === 'singleton') return <Single key={section.id} section={section} data={data} />;
  return <Cards key={section.id} section={section} data={data} />;
}

function makePage(pageId, title) {
  function ShimPage({ data }) {
    const { sections } = useCmsPreview();
    const own = sections.filter((s) => s.id.startsWith(`${pageId}.`));
    return (
      <>
        {pageId !== 'home' ? (
          <header className="s-banner">
            <h1>{title}</h1>
          </header>
        ) : null}
        {own.map((s) => render(s, data))}
      </>
    );
  }
  ShimPage.displayName = `ShimPage(${pageId})`;
  return ShimPage;
}

const TITLES = { home: 'Home', about: 'About CRTDH', team: 'Our team', innovations: 'Innovations', facilities: 'Facilities', services: 'Services', product: 'Products', enterprises: 'Enterprises', 'social-impact': 'Social impact', 'covid-19': 'Covid-19 response', media: 'Media', contact: 'Contact us' };
export const pages = Object.fromEntries(Object.entries(TITLES).map(([id, t]) => [id, makePage(id, t)]));

export function Layout({ data, children, pageId }) {
  const s = data.singletons?.['site-settings'] || {};
  const nav = visible(data.collections?.['nav-items']).filter((n) => !n.in_more).slice(0, 8);
  const tag = (id, label) => (pageId === 'site' || id.startsWith(`${pageId}.`) ? { 'data-cms-section': id, 'data-cms-tag': label } : { 'data-cms-section': id, 'data-cms-tag': label, 'data-cms-elsewhere': 'site' });
  return (
    <div className="s-root">
      <header className="s-header">
        <span className="s-logos" {...tag('site.logos', 'Logos')}>
          {s.site_logo ? <img src={s.site_logo} alt="CRTDH" height="40" /> : <strong>CRTDH</strong>}
        </span>
        <nav {...tag('site.nav', 'Menu links')}>
          {nav.map((n) => (
            <a key={n.id} href={n.url} data-cms-item={n.id}>
              {n.label}
            </a>
          ))}
        </nav>
      </header>
      <main>{children}</main>
      <footer className="s-footer">
        <div>
          <h2>CRTDH, IIT Kharagpur</h2>
          <p>{s.address}</p>
          <p>
            {s.phone_primary} · {s.email_primary}
          </p>
        </div>
        <p {...tag('site.social', 'Social links')} className="s-social">
          {['facebook_url', 'linkedin_url', 'instagram_url', 'twitter_url'].filter((k) => s[k]).map((k) => (
            <a key={k} href={s[k]}>
              {k.split('_')[0]}
            </a>
          ))}
          {!['facebook_url', 'linkedin_url', 'instagram_url', 'twitter_url'].some((k) => s[k]) ? 'Follow CRTDH' : null}
        </p>
      </footer>
    </div>
  );
}
