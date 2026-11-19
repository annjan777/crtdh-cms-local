// Roles from the API are cumulative (["editor", "publisher", "admin"]); the
// highest one is the person's role. Deactivated users have none.
export const ROLE_ORDER = ['editor', 'publisher', 'admin'];
export const ROLE_LABEL = { editor: 'Editor', publisher: 'Publisher', admin: 'Admin' };

export function topRole(roles) {
  const list = Array.isArray(roles) ? roles : [];
  return [...ROLE_ORDER].reverse().find((r) => list.includes(r)) || null;
}
