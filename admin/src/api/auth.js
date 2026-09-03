import apiClient, { setTokens, clearTokens } from './client';

export async function login(username, password) {
  const { data } = await apiClient.post('/auth/token/', { username, password });
  setTokens({ access: data.access, refresh: data.refresh });
  return data;
}

export async function fetchMe() {
  const { data } = await apiClient.get('/auth/me/');
  return data;
}

export function logout() {
  clearTokens();
}
