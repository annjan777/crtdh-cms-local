import apiClient from './client';

// Thin generic helpers shared by every resource screen. `endpoint` is the
// resource's root path, e.g. "/nav-items/".

export async function listResource(endpoint, params) {
  const { data } = await apiClient.get(endpoint, { params });
  // DRF PageNumberPagination shape: {count, next, previous, results}.
  // page_size=100 per the contract, so a single page covers every resource
  // in this CMS (largest is enterprises); results is used as-is.
  return Array.isArray(data) ? data : data.results;
}

// Same as listResource but keeps the full DRF pagination envelope so a list
// screen can show a total count and — for the rare resource with more than
// one page (page_size=100) — fetch additional pages.
export async function listResourcePage(endpoint, params) {
  const { data } = await apiClient.get(endpoint, { params });
  if (Array.isArray(data)) {
    return { results: data, count: data.length, next: null, previous: null };
  }
  return data;
}

// Cheap total-count lookup for dashboard stat tiles: asks for a single row
// so the payload stays tiny while `count` still reflects the full total.
export async function countResource(endpoint) {
  const { data } = await apiClient.get(endpoint, { params: { page_size: 1 } });
  if (Array.isArray(data)) return data.length;
  return data.count ?? data.results?.length ?? 0;
}

export async function getResource(endpoint, id) {
  const { data } = await apiClient.get(`${endpoint}${id}/`);
  return data;
}

// Builds either a plain JSON payload or a multipart FormData payload
// depending on whether any field in `values` is a File (image/file upload).
// File-valued fields that are null/unchanged are omitted entirely so a
// PATCH never clobbers an existing image with an empty value.
function buildPayload(values) {
  const hasFile = Object.values(values).some((v) => v instanceof File);
  if (!hasFile) {
    return values;
  }
  const formData = new FormData();
  Object.entries(values).forEach(([key, value]) => {
    if (value === undefined) return;
    if (value === null) return; // omit — don't send empty file/FK fields
    if (value instanceof File) {
      formData.append(key, value);
    } else {
      formData.append(key, value);
    }
  });
  return formData;
}

export async function createResource(endpoint, values) {
  const payload = buildPayload(values);
  const { data } = await apiClient.post(endpoint, payload);
  return data;
}

export async function updateResource(endpoint, id, values) {
  const payload = buildPayload(values);
  const { data } = await apiClient.patch(`${endpoint}${id}/`, payload);
  return data;
}

export async function deleteResource(endpoint, id) {
  await apiClient.delete(`${endpoint}${id}/`);
}

export async function reorderResource(endpoint, orderedIds) {
  await apiClient.post(`${endpoint}reorder/`, { order: orderedIds });
}
