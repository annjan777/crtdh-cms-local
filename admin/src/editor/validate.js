// Pure field rules shared by the field renderer and autosave. Messages lead
// with the fix and never blame the person typing.

export const plain = (v) => String(v ?? '').replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ');

export function lower(label) {
  return label.charAt(0).toLowerCase() + label.slice(1);
}

export function isValidUrl(v) {
  if (!v) return true;
  return /^\/(?![/\\])[^\s]*$/.test(v) || /^https?:\/\/[^\s.]+\.[^\s]+$/.test(v) || /^mailto:[^\s@]+@[^\s@]+$/.test(v);
}

/** Returns an error string or null. */
export function validateField(field, value) {
  const empty = value === null || value === undefined || plain(value).trim() === '';
  if (field.type === 'boolean') return null;
  if (field.required && empty && field.type !== 'image') return `Enter ${lower(field.label)}.`;
  if (empty) return null;
  if (field.max && ['text', 'textarea', 'richtext'].includes(field.type)) {
    const n = plain(value).length;
    if (n > field.max) return `Shorten to ${field.max} characters (now ${n}).`;
  }
  if (field.type === 'url' && !isValidUrl(String(value).trim()))
    return 'Use a page on this site like /innovations, or a full address starting https://.';
  if (field.type === 'number' && Number.isNaN(Number(value))) return 'Enter a number, like 12.';
  if (field.type === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'Enter a date like 28 Nov 2026.';
  return null;
}

export const WARN_WIDTH = 1200;

/**
 * Size rule for a chosen photo (plan WS2.6): a field with min_width rejects
 * anything narrower; every other image warns below 1200 px but is allowed.
 * -> { level: 'reject' | 'warn' | 'ok', message }
 */
export function checkImageSize(field, width) {
  if (!width) return { level: 'ok', message: '' };
  if (field.min_width && width < field.min_width)
    return {
      level: 'reject',
      message: `This photo is ${width} px wide. ${field.label}s in this section need at least ${field.min_width} px so they stay sharp on large screens. Your current photo is kept.`,
    };
  const warn = field.warn_width || WARN_WIDTH;
  if (width < warn)
    return { level: 'warn', message: `This photo is ${width} px wide and may look soft on large screens. ${warn} px or more is better.` };
  return { level: 'ok', message: '' };
}

export const POSITIONS = [
  ['left top', 'Top left'],
  ['center top', 'Top'],
  ['right top', 'Top right'],
  ['left center', 'Left'],
  ['center center', 'Centre'],
  ['right center', 'Right'],
  ['left bottom', 'Bottom left'],
  ['center bottom', 'Bottom'],
  ['right bottom', 'Bottom right'],
];

export function normalisePosition(v) {
  const s = String(v || 'center center').trim().toLowerCase();
  const map = { center: 'center center', top: 'center top', bottom: 'center bottom', left: 'left center', right: 'right center' };
  if (map[s]) return map[s];
  const [a, b] = s.split(/\s+/);
  // CSS allows "top left": reorder to x y.
  if (['top', 'bottom'].includes(a) && b) return `${b} ${a}`;
  return POSITIONS.some(([p]) => p === s) ? s : 'center center';
}
