// Human-readable name for a content item, used to name it in delete confirmations.
const LABEL_KEYS = ['title', 'name', 'label', 'heading', 'text', 'caption'];

export function itemLabel(item, maxLength = 60) {
  if (!item) return '';
  for (const key of LABEL_KEYS) {
    const value = item[key];
    if (typeof value === 'string' && value.trim()) {
      const clean = value.replace(/<[^>]*>/g, '').trim();
      return clean.length > maxLength ? `${clean.slice(0, maxLength - 1)}…` : clean;
    }
  }
  return '';
}

// "Delete ‘ChestXAI’?" — falls back to "Delete this <thing>?" when the item has no name.
export function deleteTitle(item, fallbackNoun) {
  const label = itemLabel(item);
  return label ? `Delete ‘${label}’?` : `Delete this ${fallbackNoun}?`;
}
