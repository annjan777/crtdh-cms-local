import { useEffect, useRef, useState } from 'react';

// Reusable image/file upload widget: shows a preview of the current value
// (an existing absolute URL from the API, or a freshly-picked File) and
// lets staff replace it with a plain file input. `isImage` toggles between
// an image thumbnail preview and a plain filename chip (used for the
// `file` field type — PDFs, video files).
export default function ImageUploadField({ value, onChange, isImage = true, required }) {
  const inputRef = useRef(null);
  const [previewUrl, setPreviewUrl] = useState(null);

  useEffect(() => {
    if (value instanceof File) {
      const url = URL.createObjectURL(value);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    if (typeof value === 'string' && value) {
      setPreviewUrl(value);
    } else {
      setPreviewUrl(null);
    }
    return undefined;
  }, [value]);

  const currentName = value instanceof File ? value.name : previewUrl ? previewUrl.split('/').pop() : null;

  return (
    <div className="upload-field">
      {isImage ? (
        <div className="upload-preview">
          {previewUrl ? (
            <img src={previewUrl} alt="Preview" />
          ) : (
            <div className="upload-preview-empty">No image</div>
          )}
        </div>
      ) : (
        currentName && <div className="upload-filename">{currentName}</div>
      )}
      <div className="upload-actions">
        <input
          ref={inputRef}
          type="file"
          accept={isImage ? 'image/*' : undefined}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onChange(file);
          }}
        />
        {value && (
          <button
            type="button"
            className="btn btn-ghost btn-small"
            onClick={() => {
              onChange(null);
              if (inputRef.current) inputRef.current.value = '';
            }}
          >
            Remove
          </button>
        )}
      </div>
      {required && !value && <span className="field-hint">Required</span>}
    </div>
  );
}
