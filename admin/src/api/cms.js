// One function per contract §3 endpoint the admin uses. Extras are from
// team/CONTRACT-ADDENDUM-1.md (A1-A9).

import { api } from './client.js';

const SINGLETONS = new Set(['site-settings', 'about-page', 'home-page']);
const rowPath = (resource, pk) => (SINGLETONS.has(resource) ? `/${resource}/` : `/${resource}/${pk}/`);

export const auth = {
  me: () => api.get('/auth/me/'),
  login: (username, password) => api.post('/auth/login/', { username, password }),
  mfa: (code) => api.post('/auth/mfa/', { code }),
  logout: () => api.post('/auth/logout/', {}),
  // Addendum A6: enrolment for a first sign-in
  mfaSetup: () => api.post('/auth/mfa/enrol/', {}),
  mfaConfirm: (code) => api.post('/auth/mfa/enrol/confirm/', { code }),
};

export const cms = {
  pages: () => api.get('/cms/pages/'),
  page: (id) => api.get(`/cms/pages/${id}/`),
  preview: (id) => api.get(`/cms/preview/${id}/`),
  changes: () => api.get('/cms/changes/'),
  discardItem: (item_id) => api.post('/cms/changes/discard/', { item_id }),
  discardSession: (session_id) => api.post('/cms/changes/discard/', { session_id }),
  requestReview: (note) => api.post('/cms/review-requests/', { note }),
  publish: (confirm_shrink = false) => api.post('/cms/publish/', { confirm_shrink }),
  publishStatus: (id) => api.get(`/cms/publish/${id}/`),
  snapshots: () => api.get('/cms/snapshots/'),
  restore: (id) => api.post(`/cms/snapshots/${id}/restore/`, {}),
  audit: (itemId) => api.get(`/cms/audit/?item_id=${encodeURIComponent(itemId)}`),
};

export const content = {
  update: (resource, pk, values, expected_version) => api.patch(rowPath(resource, pk), { ...values, expected_version }),
  upload: (resource, pk, field, file, extra, expected_version) => {
    const form = new FormData();
    form.append(field, file);
    for (const [k, v] of Object.entries(extra || {})) form.append(k, v ?? '');
    form.append('expected_version', String(expected_version));
    return api.patchForm(rowPath(resource, pk), form);
  },
  create: (resource, values) => api.post(`/${resource}/`, values),
  reorder: (resource, ids) => api.post(`/${resource}/reorder/`, { order: ids }),
  remove: (resource, pk) => api.del(`/${resource}/${pk}/`),
  list: (resource) => api.get(`/${resource}/`),
};

// Addendum A7: user management (admin role)
export const users = {
  list: () => api.get('/users/'),
  create: (values) => api.post('/users/', values),
  update: (id, values) => api.patch(`/users/${id}/`, values),
};
