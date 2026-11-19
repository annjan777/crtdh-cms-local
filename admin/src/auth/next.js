// `?next=` from the MCP lane's OAuth flow (/cms/login?next=...). Only a
// same-origin path is accepted: one leading "/", never "//", "/\", or a scheme.
export function safeNext(value) {
  if (typeof value !== 'string' || !value.startsWith('/')) return null;
  if (value.startsWith('//') || value.startsWith('/\\')) return null;
  if ([...value].some((c) => c.charCodeAt(0) < 0x20)) return null;
  return value;
}

export function nextFromLocation(search = typeof window !== 'undefined' ? window.location.search : '') {
  return safeNext(new URLSearchParams(search).get('next'));
}
