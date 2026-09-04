import axios from 'axios';

// API base URL — override via .env / .env.local with VITE_API_BASE_URL.
// Falls back to the Django dev server default from API_CONTRACT.md.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
export const PUBLIC_SITE_URL =
  import.meta.env.VITE_PUBLIC_SITE_URL ||
  (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}` : 'http://localhost:3000');

const ACCESS_KEY = 'crtdh_admin_access';
const REFRESH_KEY = 'crtdh_admin_refresh';

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// Main client used for all resource calls — carries the access token and
// silently refreshes it on a 401.
const apiClient = axios.create({ baseURL: API_BASE_URL });

// Bare instance (no interceptors) used only for the refresh call itself,
// so a failed refresh can never recursively trigger another refresh.
const refreshClient = axios.create({ baseURL: API_BASE_URL });

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise = null;

function goToLogin() {
  clearTokens();
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.assign('/login');
  }
}

async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) {
    throw new Error('No refresh token available');
  }
  const { data } = await refreshClient.post('/auth/token/refresh/', { refresh });
  setTokens({ access: data.access });
  return data.access;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;

    const isAuthEndpoint = config?.url?.includes('/auth/token');
    if (!response || response.status !== 401 || !config || config._retry || isAuthEndpoint) {
      return Promise.reject(error);
    }

    config._retry = true;
    try {
      // Coalesce concurrent 401s into a single refresh call.
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }
      const newAccess = await refreshPromise;
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${newAccess}`;
      return apiClient(config);
    } catch (refreshError) {
      goToLogin();
      return Promise.reject(refreshError);
    }
  },
);

export async function fetchList(endpoint, params) {
  const { data } = await apiClient.get(endpoint, { params });
  return Array.isArray(data) ? data : data.results || [];
}

export async function fetchOne(endpoint, id = '') {
  const url = id ? `${endpoint.replace(/\/$/, '')}/${id}/` : endpoint;
  const { data } = await apiClient.get(url);
  return data;
}

function isExistingFileUrl(value) {
  if (typeof value !== 'string') return false;
  return value.startsWith('http://') || value.startsWith('https://') || value.startsWith('/media/') || value.startsWith('blob:');
}

function buildPayload(values) {
  if (!values || typeof values !== 'object') return values;
  const hasFile = Object.values(values).some((v) => v instanceof File);
  if (!hasFile) {
    const out = {};
    Object.entries(values).forEach(([key, value]) => {
      if (key.endsWith('_preview')) return;
      if (isExistingFileUrl(value)) return;
      out[key] = value;
    });
    return out;
  }
  const formData = new FormData();
  Object.entries(values).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    if (key.endsWith('_preview')) return;
    if (value instanceof File) {
      formData.append(key, value);
    } else if (!isExistingFileUrl(value)) {
      formData.append(key, value);
    }
  });
  return formData;
}

export async function createOne(endpoint, values) {
  const payload = buildPayload(values);
  const { data } = await apiClient.post(endpoint, payload);
  return data;
}

export async function updateOne(endpoint, id, values) {
  const url = id ? `${endpoint.replace(/\/$/, '')}/${id}/` : endpoint;
  const payload = buildPayload(values);
  const { data } = await apiClient.patch(url, payload);
  return data;
}

export async function deleteOne(endpoint, id) {
  const url = id ? `${endpoint.replace(/\/$/, '')}/${id}/` : endpoint;
  const { data } = await apiClient.delete(url);
  return data;
}

export async function uploadFile(file) {
  if (file instanceof File) {
    return { url: URL.createObjectURL(file), file };
  }
  return { url: file };
}

export default apiClient;
