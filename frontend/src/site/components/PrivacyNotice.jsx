import SiteLink from '../link.jsx'

// Contact-form privacy notice (the short notice in docs/privacy-notice.md, passed in as data.extra.privacy).

/** Short notice, shown directly above Send (docs/privacy-notice.md). */
export function ShortNotice({ privacy }) {
  const text = privacy?.short || 'What you send here goes to the CRTDH office at IIT Kharagpur and is used only to reply to you.'
  // The full notice is not shown on the site, so a link to it (#privacy) would go nowhere: keep the text only.
  return <p className="privacy small soft" id="contact-notice">{inlineLinks(text.replace(/\s*\[[^\]]+\]\(#privacy\)/g, ''))}</p>
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
