import { hasMarkup, sanitizeRichText } from '../richtext.js'

/**
 * A CMS rich-text field. Plain text becomes paragraphs (blank line = new paragraph); HTML from the editor
 * is rebuilt from an allow-list by sanitizeRichText before it is rendered.
 */
export default function RichText({ html, className = '' }) {
  if (!html) return null
  if (!hasMarkup(html)) {
    const paragraphs = String(html).split(/\n{2,}/).map((p) => p.trim()).filter(Boolean)
    return (
      <div className={className}>
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    )
  }
  const clean = sanitizeRichText(html)
  if (!clean.trim()) return null
  // nosemgrep: crtdh-no-dangerously-set-inner-html, typescript.react.security.audit.react-dangerouslysetinnerhtml.react-dangerouslysetinnerhtml -- rebuilt from an allow-list by sanitizeRichText (src/site/richtext.js); backend clean_richtext on write
  return <div className={className} dangerouslySetInnerHTML={{ __html: clean }} />
}
