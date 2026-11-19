import PageShell from '../components/PageShell.jsx'
import SiteLink from '../link.jsx'
import ContactForm from '../components/ContactForm.jsx'
import { MapEmbed, PageBanner } from '../components/Blocks.jsx'

/** Contact (form pattern): the form, then address and map. */
export default function Contact({ data, settings: settingsProp }) {
  // Site settings come from the layout data; the admin preview may pass them directly.
  const settings = settingsProp || data.singletons?.['site-settings'] || data.layout?.singletons?.['site-settings'] || {}
  const privacy = data.extra?.privacy
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
          <ContactForm email={settings.email_primary} phone={settings.phone_primary} notice={<ShortNotice privacy={privacy} />} />
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
            <MapEmbed src={settings.map_embed_url} address={settings.address} />
          </aside>
        </div>
      </section>
      <FullNotice privacy={privacy} />
    </PageShell>
  )
}

/** Short notice, shown directly above Send (docs/privacy-notice.md). */
function ShortNotice({ privacy }) {
  const text = privacy?.short || 'What you send here goes to the CRTDH office at IIT Kharagpur and is used only to reply to you.'
  return <p className="privacy small soft" id="contact-notice">{inlineLinks(text)}</p>
}

/** Full notice: "How we use your message" at /contact#privacy. Hidden until the document exists. */
function FullNotice({ privacy }) {
  if (!privacy?.paragraphs?.length) return null
  return (
    <section className="section section--surface" id="privacy" aria-labelledby="privacy-title">
      <div className="wrap">
        <h2 id="privacy-title">{privacy.title}</h2>
        <div className="prose mt-6">
          {privacy.paragraphs.map((p, i) => (
            <p key={i}>{inlineLinks(p)}</p>
          ))}
        </div>
      </div>
    </section>
  )
}

function inlineLinks(text) {
  const out = []
  const re = /\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*/g
  let last = 0
  let m
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index))
    if (m[1]) out.push(<SiteLink key={m.index} to={m[2]}>{m[1]}</SiteLink>)
    else out.push(<strong key={m.index}>{m[3]}</strong>)
    last = re.lastIndex
  }
  out.push(text.slice(last))
  return out
}
