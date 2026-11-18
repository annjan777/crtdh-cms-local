"""Contract §4 error bodies for every API response (the one exception handler).

    raise CMSError("CMS_STALE_VERSION", "...", current_version=8)
    error_response("CMS_NOT_FOUND", "Not found.")
    as_error_body(exc)   # for MCP structuredContent / non-DRF callers

apps.publishing.errors re-exports these names. Bodies never carry secrets,
tokens, signed URLs or tracebacks.
"""
import logging
import uuid

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response

logger = logging.getLogger("crtdh.security")

STATUS = {
    "CMS_VALIDATION": 400,
    "CMS_UNAUTHENTICATED": 401,
    "CMS_MFA_REQUIRED": 401,
    "CMS_FORBIDDEN_ROLE": 403,
    "CMS_CSRF_FAILED": 403,
    "CMS_NOT_FOUND": 404,
    "CMS_STALE_VERSION": 409,
    "CMS_PUBLISH_RUNNING": 409,
    "CMS_IMAGE_TOO_SMALL": 400,
    "CMS_FETCH_BLOCKED": 400,
    "CMS_RATE_LIMITED": 429,
    "CMS_SESSION_LIMIT": 429,
    "CMS_BUILD_GUARD": 422,
    "CMS_INTERNAL": 500,
}
STATUS_BY_CODE = STATUS  # older name

DEFAULT_FIX = {
    "CMS_VALIDATION": "Correct the field and try again.",
    "CMS_UNAUTHENTICATED": "Sign in to the CMS and try again.",
    "CMS_MFA_REQUIRED": "Set up your authenticator app, then sign in.",
    "CMS_FORBIDDEN_ROLE": "Ask a CMS admin for the role this action needs.",
    "CMS_CSRF_FAILED": "Fetch /api/v1/auth/csrf/ and resend with the X-CSRFToken header.",
    "CMS_NOT_FOUND": "Reload the page; the item may have been removed.",
    "CMS_STALE_VERSION": "Reload the section and reapply your change.",
    "CMS_PUBLISH_RUNNING": "Wait for the running publish to finish, then publish again.",
    "CMS_IMAGE_TOO_SMALL": "Upload the original photo (2400 px or wider is best).",
    "CMS_RATE_LIMITED": "Wait a minute and try again.",
    "CMS_BUILD_GUARD": "Check the listed collections; publish again with confirm_shrink if the removals are intended.",
    "CMS_INTERNAL": "Try again; if it keeps failing, tell the site maintainer the request id.",
}


def new_request_id():
    return uuid.uuid4().hex


def error_body(code, message, *, fix=None, retryable=False, side_effects="none", field=None,
               current_version=None, request_id=None):
    return {
        "code": code,
        "message": message,
        "fix": fix or DEFAULT_FIX.get(code, "Try again."),
        "retryable": retryable,
        "side_effects": side_effects,
        "field": field,
        "current_version": current_version,
        # Always set (contract §4): bodies built outside a request (plain Django views, MCP) get a fresh id.
        "request_id": request_id or new_request_id(),
    }


class CMSError(exceptions.APIException):
    """Raise anywhere in a DRF view (or MCP tool): rendered as the contract error body."""

    def __init__(self, code, message, *, status_code=None, headers=None, extra=None, **kw):
        """`extra`: contract-addendum keys for specific codes (e.g. locked_until, edited_by, publish_id)."""
        self.code = code
        self.status_code = status_code or STATUS.get(code, 400)
        self.body = error_body(code, message, **kw)
        self.body.update(extra or {})
        self.headers = headers or {}
        super().__init__(detail=message, code=code)


def _rid(request):
    return getattr(request, "request_id", None) or new_request_id()


def error_response(code, message, *, request=None, http_status=None, headers=None, **kw):
    kw.setdefault("request_id", _rid(request))
    return Response(error_body(code, message, **kw), status=http_status or STATUS[code], headers=headers)


def _validation_message(detail, prefix=""):
    """Flatten DRF validation detail into (first_field, 'field: msg; other: msg')."""
    parts, first = [], None
    if isinstance(detail, dict):
        for key, value in detail.items():
            name = f"{prefix}{key}" if key != "non_field_errors" else prefix.rstrip(".") or None
            sub_first, sub_msg = _validation_message(value, f"{name}." if name else "")
            first = first or sub_first or name
            parts.append(f"{name}: {sub_msg}" if name and not isinstance(value, dict) else sub_msg)
    elif isinstance(detail, list):
        msgs = []
        for v in detail:
            f, m = _validation_message(v, prefix)
            first = first or f
            msgs.append(m)
        return first, " ".join(msgs)
    else:
        return None, str(detail)
    return first, "; ".join(p for p in parts if p)


def exception_handler(exc, context):
    request = (context or {}).get("request")
    if isinstance(exc, CMSError):
        body = dict(exc.body)
        # Prefer the id of the request being answered (matches X-Request-ID) over one minted at raise time.
        body["request_id"] = getattr(request, "request_id", None) or body.get("request_id") or new_request_id()
        return Response(body, status=exc.status_code, headers=exc.headers)
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        return error_response("CMS_UNAUTHENTICATED", "You are not signed in, or your session has expired.",
                              request=request, headers={"WWW-Authenticate": "Session"})
    if isinstance(exc, exceptions.PermissionDenied):
        detail = str(exc.detail)
        if detail.startswith("CSRF Failed"):
            return error_response("CMS_CSRF_FAILED", "Security token missing or expired.", request=request,
                                  retryable=True)
        msg = detail if exc.detail != exceptions.PermissionDenied.default_detail else "Your role does not allow this action."
        return error_response("CMS_FORBIDDEN_ROLE", msg, request=request)
    if isinstance(exc, exceptions.NotFound):
        return error_response("CMS_NOT_FOUND", "Not found.", request=request)
    if isinstance(exc, exceptions.Throttled):
        wait = int(exc.wait or 60)
        return error_response("CMS_RATE_LIMITED", f"Too many requests. Try again in {wait} seconds.",
                              request=request, retryable=True, headers={"Retry-After": str(wait)})
    if isinstance(exc, exceptions.ValidationError):
        field, message = _validation_message(exc.detail)
        return error_response("CMS_VALIDATION", message or "Invalid input.", request=request, field=field)
    if isinstance(exc, exceptions.MethodNotAllowed):
        return error_response("CMS_VALIDATION", str(exc.detail), request=request, fix="Use a supported HTTP method.",
                              http_status=status.HTTP_405_METHOD_NOT_ALLOWED)
    if isinstance(exc, exceptions.APIException):
        code = "CMS_VALIDATION" if exc.status_code < 500 else "CMS_INTERNAL"
        return error_response(code, str(exc.detail), request=request, http_status=exc.status_code)

    rid = _rid(request)
    logger.exception("unhandled API error request_id=%s", rid)
    return error_response("CMS_INTERNAL", "Something went wrong on the server.", retryable=True,
                          side_effects="unknown", request_id=rid)


def as_error_body(exc):
    """Any exception -> contract §4 body (for MCP structuredContent and non-DRF callers)."""
    resp = exception_handler(exc, {})
    return resp.data


def csrf_failure(request, reason=""):
    """Django-level CSRF failures (non-DRF views) get the same JSON body."""
    return JsonResponse(error_body("CMS_CSRF_FAILED", "Security token missing or expired.", retryable=True,
                                   request_id=_rid(request)), status=403)
