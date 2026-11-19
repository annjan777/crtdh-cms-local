// Error mapping for contract §4. Every failure the UI sees is an ApiError with
// a stable `code`; screens pick their recovery from the code, never from the
// HTTP status alone.

export const CODES = [
  'CMS_VALIDATION',
  'CMS_UNAUTHENTICATED',
  'CMS_MFA_REQUIRED',
  'CMS_CSRF_FAILED',
  'CMS_FORBIDDEN_ROLE',
  'CMS_NOT_FOUND',
  'CMS_STALE_VERSION',
  'CMS_PUBLISH_RUNNING',
  'CMS_IMAGE_TOO_SMALL',
  'CMS_FETCH_BLOCKED',
  'CMS_RATE_LIMITED',
  'CMS_SESSION_LIMIT',
  'CMS_BUILD_GUARD',
  'CMS_INTERNAL',
];

// Client-side codes (never sent by the server).
export const NETWORK = 'NETWORK';

const STATUS_FALLBACK = {
  400: 'CMS_VALIDATION',
  401: 'CMS_UNAUTHENTICATED',
  403: 'CMS_FORBIDDEN_ROLE',
  404: 'CMS_NOT_FOUND',
  409: 'CMS_STALE_VERSION',
  422: 'CMS_BUILD_GUARD',
  429: 'CMS_RATE_LIMITED',
};

// Plain-language defaults, used only when the server sent no message.
const DEFAULT_MESSAGE = {
  CMS_VALIDATION: 'Some of this can’t be saved as it is.',
  CMS_UNAUTHENTICATED: 'You’ve been signed out.',
  CMS_MFA_REQUIRED: 'Two-step sign-in isn’t finished.',
  CMS_CSRF_FAILED: 'This page’s security check expired.',
  CMS_FORBIDDEN_ROLE: 'Your role can’t do this.',
  CMS_NOT_FOUND: 'This item no longer exists.',
  CMS_STALE_VERSION: 'Someone else changed this since you opened it.',
  CMS_PUBLISH_RUNNING: 'A publish is already running.',
  CMS_IMAGE_TOO_SMALL: 'This photo is too small.',
  CMS_FETCH_BLOCKED: 'That address can’t be fetched.',
  CMS_RATE_LIMITED: 'Too many attempts in a short time.',
  CMS_SESSION_LIMIT: 'This Claude session has reached its change limit.',
  CMS_BUILD_GUARD: 'The build stopped before anything was uploaded.',
  CMS_INTERNAL: 'Something went wrong on the server.',
  NETWORK: 'The CMS can’t be reached.',
};

const DEFAULT_FIX = {
  CMS_VALIDATION: 'Check the highlighted field.',
  CMS_UNAUTHENTICATED: 'Sign in again. Your unsaved text is kept on this computer.',
  CMS_MFA_REQUIRED: 'Sign in again and enter the code from your authenticator app.',
  CMS_CSRF_FAILED: 'Try again. If it keeps happening, reload the page.',
  CMS_FORBIDDEN_ROLE: 'Ask a Publisher or Admin.',
  CMS_NOT_FOUND: 'Reload the page.',
  CMS_STALE_VERSION: 'Reload the section and apply your change again.',
  CMS_PUBLISH_RUNNING: 'Wait for it to finish.',
  CMS_IMAGE_TOO_SMALL: 'Choose a larger photo.',
  CMS_FETCH_BLOCKED: 'Upload the file instead.',
  CMS_RATE_LIMITED: 'Wait a minute and try again.',
  CMS_SESSION_LIMIT: 'Review and publish, or discard, the changes so far.',
  CMS_BUILD_GUARD: 'Check the changes, then confirm to publish anyway.',
  CMS_INTERNAL: 'Try again. If it keeps happening, copy the error details for support.',
  NETWORK: 'Check the connection. Your text is kept on this computer and saves when you’re back.',
};

const RETRYABLE_DEFAULT = new Set(['CMS_CSRF_FAILED', 'CMS_RATE_LIMITED', 'CMS_INTERNAL', 'NETWORK', 'CMS_PUBLISH_RUNNING']);

export class ApiError extends Error {
  constructor({ code, message, fix, retryable, status, field, currentVersion, requestId, sideEffects, details }) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.fix = fix;
    this.retryable = retryable;
    this.status = status;
    this.field = field ?? null;
    this.currentVersion = currentVersion ?? null;
    this.requestId = requestId ?? null;
    this.sideEffects = sideEffects ?? null;
    this.details = details ?? {};
  }

  // Text for "Copy error details": identifiers only, never response bodies.
  supportText(route = typeof window !== 'undefined' ? window.location.pathname : '') {
    return JSON.stringify(
      { code: this.code, status: this.status, request_id: this.requestId, at: new Date().toISOString(), route },
      null,
      1,
    );
  }
}

/**
 * Build an ApiError from an HTTP status and a parsed JSON body (or null when
 * the body was missing or not JSON). Unknown codes fall back by status.
 */
export function mapError(status, body) {
  const b = body && typeof body === 'object' ? body : {};
  let code = typeof b.code === 'string' && CODES.includes(b.code) ? b.code : null;
  if (!code) code = STATUS_FALLBACK[status] || (status >= 500 ? 'CMS_INTERNAL' : 'CMS_INTERNAL');
  // A 409 that names a publish is a running publish, whatever the body says.
  if (status === 409 && !b.code && b.publish_id) code = 'CMS_PUBLISH_RUNNING';
  const known = typeof b.message === 'string' && b.message.length > 0 && b.message.length < 400;
  const { code: _c, message: _m, fix: _f, retryable: _r, side_effects: _s, field: _fd, current_version: _cv, request_id: _rid, ...details } = b;
  return new ApiError({
    code,
    status,
    message: known ? b.message : DEFAULT_MESSAGE[code],
    fix: typeof b.fix === 'string' && b.fix ? b.fix : DEFAULT_FIX[code],
    retryable: typeof b.retryable === 'boolean' ? b.retryable : RETRYABLE_DEFAULT.has(code),
    field: b.field,
    currentVersion: b.current_version,
    requestId: b.request_id,
    sideEffects: b.side_effects,
    details,
  });
}

export function networkError() {
  return new ApiError({
    code: NETWORK,
    status: 0,
    message: DEFAULT_MESSAGE.NETWORK,
    fix: DEFAULT_FIX.NETWORK,
    retryable: true,
  });
}
