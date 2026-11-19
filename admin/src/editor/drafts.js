// Unsaved text kept on this computer (offline, or signed out by inactivity).
// Keyed by user so a shared lab PC never shows one person's draft to another;
// cleared on an explicit sign-out, kept on session expiry.
const PREFIX = 'crtdh-draft:';
let owner = null;

export function setDraftOwner(userId) {
  owner = userId ?? null;
}
const full = (key) => (owner === null ? null : `${PREFIX}${owner}:${key}`);

export function readDraft(key) {
  const k = full(key);
  if (!k) return null;
  try {
    return JSON.parse(localStorage.getItem(k) || 'null');
  } catch {
    return null;
  }
}
export function writeDraft(key, values, baseVersion) {
  const k = full(key);
  if (!k) return;
  try {
    localStorage.setItem(k, JSON.stringify({ values, base_version: baseVersion, at: new Date().toISOString() }));
  } catch {
    /* storage full: the in-memory copy still exists */
  }
}
export function clearDraft(key) {
  const k = full(key);
  if (k) localStorage.removeItem(k);
}
/** Remove every draft of one user (on sign-out). */
export function clearUserDrafts(userId) {
  if (userId === null || userId === undefined) return;
  const p = `${PREFIX}${userId}:`;
  for (const k of Object.keys(localStorage)) if (k.startsWith(p)) localStorage.removeItem(k);
}
