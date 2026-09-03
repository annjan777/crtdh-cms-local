import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { useEffect } from 'react';

// Minimal Tiptap-based rich text editor for Innovation.body. Produces
// sanitized-on-save HTML (the backend runs bleach on save per the plan);
// this editor's job is just to give staff real WYSIWYG formatting instead
// of a raw HTML textarea.
export default function RichTextEditor({ value, onChange }) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: value || '',
    onUpdate: ({ editor: ed }) => {
      onChange(ed.getHTML());
    },
  });

  // Keep the editor in sync if `value` changes externally (e.g. loading a
  // different record) without fighting the user's own typing.
  useEffect(() => {
    if (editor && value !== editor.getHTML() && document.activeElement?.closest('.rte') == null) {
      editor.commands.setContent(value || '', { emitUpdate: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, editor]);

  if (!editor) return null;

  const button = (label, action, isActive) => (
    <button
      type="button"
      className={`rte-btn${isActive ? ' active' : ''}`}
      onMouseDown={(e) => {
        e.preventDefault();
        action();
      }}
    >
      {label}
    </button>
  );

  return (
    <div className="rte">
      <div className="rte-toolbar">
        {button('B', () => editor.chain().focus().toggleBold().run(), editor.isActive('bold'))}
        {button('I', () => editor.chain().focus().toggleItalic().run(), editor.isActive('italic'))}
        {button('H2', () => editor.chain().focus().toggleHeading({ level: 2 }).run(), editor.isActive('heading', { level: 2 }))}
        {button('H3', () => editor.chain().focus().toggleHeading({ level: 3 }).run(), editor.isActive('heading', { level: 3 }))}
        {button('• List', () => editor.chain().focus().toggleBulletList().run(), editor.isActive('bulletList'))}
        {button('1. List', () => editor.chain().focus().toggleOrderedList().run(), editor.isActive('orderedList'))}
        {button('“ ”', () => editor.chain().focus().toggleBlockquote().run(), editor.isActive('blockquote'))}
        {button('Clear', () => editor.chain().focus().clearNodes().unsetAllMarks().run(), false)}
      </div>
      <EditorContent editor={editor} className="rte-content" />
    </div>
  );
}
