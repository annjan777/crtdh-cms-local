import SiteLink from '../link.jsx'

// Contact-form privacy notices (docs/privacy-notice.md, passed in as data.extra.privacy).

/** Short notice, shown directly above Send (docs/privacy-notice.md). */
export function ShortNotice({ privacy }) {
  const text = privacy?.short || 'What you send here goes to the CRTDH office at IIT Kharagpur and is used only to reply to you.'
  return <p className="privacy small soft" id="contact-notice">{inlineLinks(text)}</p>
}

/** Full notice: "How we use your message" at /contact#privacy. Hidden until the document exists. */
export function FullNotice({ privacy }) {
  if (!privacy?.paragraphs?.length) return null
  return (
    <section className="section" id="privacy" aria-labelledby="privacy-title">
      <div className="container">
        <h2 id="privacy-title">{privacy.title}</h2>
        <div>
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
