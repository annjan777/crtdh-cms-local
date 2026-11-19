// Rich text limited to the marks the public site allows (contract §2):
// bold, italic, link, bulleted and numbered lists, and H3. Nothing else can
// be typed or pasted in, because the editor schema has no other nodes.
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { useEffect, useRef, useState } from 'react';
import { Bold, Heading3, Italic, Link2, List, ListOrdered } from 'lucide-react';
import { IconButton } from '../../ui/index.jsx';
import { isValidUrl } from '../validate.js';

export const RICH_EXTENSIONS = [
  StarterKit.configure({
    heading: { levels: [3] },
    blockquote: false,
    code: false,
    codeBlock: false,
    horizontalRule: false,
    strike: false,
    underline: false,
    link: { openOnClick: false, autolink: true, defaultProtocol: 'https', protocols: ['http', 'https', 'mailto'] },
  }),
];

export default function RichTextField({ id, value, onChange, label, onBlur, invalid }) {
  const [linkOpen, setLinkOpen] = useState(false);
  const [href, setHref] = useState('');
  const [linkErr, setLinkErr] = useState('');
  const [, force] = useState(0);
  const linkInput = useRef(null);
  const editor = useEditor({
    extensions: RICH_EXTENSIONS,
    content: value,
    editorProps: {
      attributes: {
        id,
        class: 'rte-body',
        role: 'textbox',
        'aria-multiline': 'true',
        'aria-label': label,
        'aria-describedby': `${id}-msg`,
      },
    },
    onUpdate: ({ editor: ed }) => onChange(ed.isEmpty ? '' : ed.getHTML()),
    onSelectionUpdate: () => force((n) => n + 1),
    onBlur: () => onBlur?.(),
  });

  useEffect(() => {
    if (!editor || editor.isFocused) return;
    if ((value || '') !== (editor.isEmpty ? '' : editor.getHTML())) editor.commands.setContent(value || '', { emitUpdate: false });
  }, [value, editor]);

  useEffect(() => {
    if (linkOpen) linkInput.current?.focus();
  }, [linkOpen]);

  if (!editor) return <div className="rte skel" style={{ height: 120 }} />;
  const is = (name, attrs) => editor.isActive(name, attrs);
  const chain = () => editor.chain().focus();

  function openLink() {
    setHref(editor.getAttributes('link').href || '');
    setLinkErr('');
    setLinkOpen(true);
  }
  function applyLink(e) {
    e?.preventDefault();
    const url = href.trim();
    if (!url) {
      chain().extendMarkRange('link').unsetLink().run();
      setLinkOpen(false);
      return;
    }
    if (!isValidUrl(url)) {
      setLinkErr('Use a page like /services, or a full address starting https://.');
      return;
    }
    chain().extendMarkRange('link').setLink({ href: url }).run();
    setLinkOpen(false);
  }

  return (
    <div className={`rte${invalid ? ' is-invalid' : ''}`}>
      <div className="rte-toolbar" role="toolbar" aria-label={`${label} formatting`} aria-controls={id}>
        <IconButton label="Bold" shortcut="Ctrl+B" pressed={is('bold')} onClick={() => chain().toggleBold().run()}>
          <Bold size={16} aria-hidden="true" />
        </IconButton>
        <IconButton label="Italic" shortcut="Ctrl+I" pressed={is('italic')} onClick={() => chain().toggleItalic().run()}>
          <Italic size={16} aria-hidden="true" />
        </IconButton>
        <IconButton label="Add link" pressed={is('link')} onClick={openLink}>
          <Link2 size={16} aria-hidden="true" />
        </IconButton>
        <span className="rte-sep" aria-hidden="true" />
        <IconButton label="Bulleted list" pressed={is('bulletList')} onClick={() => chain().toggleBulletList().run()}>
          <List size={16} aria-hidden="true" />
        </IconButton>
        <IconButton label="Numbered list" pressed={is('orderedList')} onClick={() => chain().toggleOrderedList().run()}>
          <ListOrdered size={16} aria-hidden="true" />
        </IconButton>
        <IconButton label="Small heading" pressed={is('heading', { level: 3 })} onClick={() => chain().toggleHeading({ level: 3 }).run()}>
          <Heading3 size={16} aria-hidden="true" />
        </IconButton>
      </div>
      {linkOpen ? (
        <form className="rte-link" onSubmit={applyLink} onKeyDown={(e) => e.key === 'Escape' && (e.stopPropagation(), setLinkOpen(false))}>
          <label htmlFor={`${id}-href`}>Link address</label>
          <input ref={linkInput} id={`${id}-href`} value={href} placeholder="https://… or /page" onChange={(e) => { setHref(e.target.value); setLinkErr(''); }} aria-invalid={!!linkErr || undefined} aria-describedby={`${id}-href-err`} />
          <button type="submit" className="btn btn-small">
            Apply link
          </button>
          {is('link') ? (
            <button type="button" className="btn btn-small btn-quiet" onClick={() => { setHref(''); chain().extendMarkRange('link').unsetLink().run(); setLinkOpen(false); }}>
              Remove link
            </button>
          ) : null}
          {linkErr ? (
            <p className="field-error" id={`${id}-href-err`} role="alert">
              {linkErr}
            </p>
          ) : null}
        </form>
      ) : null}
      <EditorContent editor={editor} />
    </div>
  );
}
