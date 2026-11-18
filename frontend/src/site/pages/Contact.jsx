import PageShell from '../components/PageShell.jsx'
import ContactForm from '../components/ContactForm.jsx'
import { PageBanner } from '../components/Blocks.jsx'

/** Contact (form pattern): the form, then address and map. */
export default function Contact({ data, settings: settingsProp }) {
  // Site settings come from the layout data; the admin preview may pass them directly.
  const settings = settingsProp || data.singletons?.['site-settings'] || data.layout?.singletons?.['site-settings'] || {}
  const notice = data.extra?.privacyNotice
  const phones = [settings.phone_primary, settings.phone_secondary].filter(Boolean)
  const emails = [settings.email_primary, settings.email_secondary].filter(Boolean)
  return (
    <PageShell data={data} className="contact">
      <PageBanner
        title="Contact CRTDH"
        intro="Questions about our research, facilities or services, or about working with the centre: write to us and the team will reply by email."
      />
      <section className="section">
        <div className="wrap contact__grid">
          <ContactForm email={settings.email_primary} privacy={<PrivacyNotice markdown={notice} />} />
          <aside className="contact__details" aria-labelledby="contact-office">
            <h2 id="contact-office">The office</h2>
            <dl className="facts">
              {settings.address && (
                <>
                  <dt>Address</dt>
                  <dd><address>{settings.address}</address></dd>
                </>
              )}
              {phones.length > 0 && (
                <>
                  <dt>Phone</dt>
                  <dd>
                    {phones.map((p) => (
                      <a key={p} href={`tel:${p.replace(/[^\d+]/g, '')}`} className="facts__link">{p}</a>
                    ))}
                  </dd>
                </>
              )}
              {emails.length > 0 && (
                <>
                  <dt>Email</dt>
                  <dd>
                    {emails.map((e) => (
                      <a key={e} href={`mailto:${e}`} className="facts__link">{e}</a>
                    ))}
                  </dd>
                </>
              )}
            </dl>
            {settings.map_embed_url && (
              <div className="map">
                <iframe src={settings.map_embed_url} title="Map: CRTDH at IIT Kharagpur" loading="lazy" referrerPolicy="no-referrer-when-downgrade" />
              </div>
            )}
          </aside>
        </div>
      </section>
    </PageShell>
  )
}

/** Renders docs/privacy-notice.md (paragraphs and links only). Until it exists: what the form does. */
function PrivacyNotice({ markdown }) {
  if (!markdown) {
    return (
      <div className="privacy small soft">
        <p>
          What you send here goes to the CRTDH office at IIT Kharagpur and is used only to reply to you.
        </p>
      </div>
    )
  }
  const paras = markdown
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter((p) => p && !p.startsWith('#'))
  return (
    <div className="privacy small soft">
      {paras.map((p, i) => (
        <p key={i}>{inlineLinks(p.replace(/\n/g, ' '))}</p>
      ))}
    </div>
  )
}

function inlineLinks(text) {
  const out = []
  const re = /\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*/g
  let last = 0
  let m
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index))
    if (m[1]) out.push(<a key={m.index} href={m[2]}>{m[1]}</a>)
    else out.push(<strong key={m.index}>{m[3]}</strong>)
    last = re.lastIndex
  }
  out.push(text.slice(last))
  return out
}
