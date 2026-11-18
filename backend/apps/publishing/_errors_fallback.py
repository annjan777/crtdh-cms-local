"""Local copy of the contract §4 handler, used until backend-security's apps.common.errors is merged."""
import logging
import uuid

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response

log = logging.getLogger(__name__)

STATUS = {
    "CMS_VALIDATION": 400,
    "CMS_UNAUTHENTICATED": 401,
    "CMS_FORBIDDEN_ROLE": 403,
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

DEFAULT_FIX = {
    "CMS_VALIDATION": "Correct the field and try again.",
    "CMS_UNAUTHENTICATED": "Sign in to the CMS and try again.",
    "CMS_FORBIDDEN_ROLE": "Ask a CMS admin for the role this action needs.",
    "CMS_NOT_FOUND": "Reload the page; the item may have been removed.",
    "CMS_STALE_VERSION": "Reload the section and reapply your change.",
    "CMS_PUBLISH_RUNNING": "Wait for the running publish to finish, then publish again.",
    "CMS_RATE_LIMITED": "Wait a minute and try again.",
    "CMS_BUILD_GUARD": "Check the listed collections; publish again with confirm_shrink if the removals are intended.",
    "CMS_INTERNAL": "Try again; if it keeps failing, tell the site maintainer the request id.",
}


def new_request_id():
    return uuid.uuid4().hex[:16]


def error_body(code, message, *, fix=None, retryable=False, side_effects="none", field=None, current_version=None,
               request_id=None):
    body = {
        "code": code,
        "message": message,
        "fix": fix or DEFAULT_FIX.get(code, "Try again."),
        "retryable": retryable,
        "side_effects": side_effects,
        "field": field,
        "current_version": current_version,
        "request_id": request_id or new_request_id(),
    }
    return body


class CMSError(exceptions.APIException):
    """Raise anywhere in a DRF view: rendered as the contract error body."""

    def __init__(self, code, message, **kw):
        self.code = code
        self.status_code = STATUS[code]
        self.body = error_body(code, message, **kw)
        super().__init__(detail=message)


def error_response(code, message, **kw):
    return Response(error_body(code, message, **kw), status=STATUS[code])


def _validation_message(detail, prefix=""):
    """Flatten DRF validation detail into ('field', 'field: msg; other: msg')."""
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
    if isinstance(exc, CMSError):
        return Response(exc.body, status=exc.status_code)
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        return error_response("CMS_UNAUTHENTICATED", "You are not signed in, or your session has expired.")
    if isinstance(exc, exceptions.PermissionDenied):
        return error_response("CMS_FORBIDDEN_ROLE", str(exc.detail) if exc.detail != exceptions.PermissionDenied.default_detail
                              else "Your role does not allow this action.")
    if isinstance(exc, exceptions.NotFound):
        return error_response("CMS_NOT_FOUND", "Not found.")
    if isinstance(exc, exceptions.Throttled):
        resp = error_response("CMS_RATE_LIMITED", "Too many requests.", retryable=True)
        if exc.wait:
            resp["Retry-After"] = str(int(exc.wait))
        return resp
    if isinstance(exc, exceptions.ValidationError):
        field, message = _validation_message(exc.detail)
        return error_response("CMS_VALIDATION", message or "Invalid input.", field=field)
    if isinstance(exc, (exceptions.ParseError, exceptions.UnsupportedMediaType)):
        return error_response("CMS_VALIDATION", str(exc.detail))
    if isinstance(exc, exceptions.MethodNotAllowed):
        body = error_body("CMS_VALIDATION", str(exc.detail), fix="Use a supported HTTP method.")
        return Response(body, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    if isinstance(exc, exceptions.APIException):
        body = error_body("CMS_VALIDATION" if exc.status_code < 500 else "CMS_INTERNAL", str(exc.detail))
        return Response(body, status=exc.status_code)
    rid = new_request_id()
    log.exception("Unhandled API error (request_id=%s)", rid)
    return error_response("CMS_INTERNAL", "Something went wrong on the server.", retryable=True, side_effects="unknown",
                          request_id=rid)


def as_error_body(exc):
    """Any exception -> contract §4 body (for MCP structuredContent and non-DRF callers)."""
    if isinstance(exc, CMSError):
        return exc.body
    resp = exception_handler(exc, {})
    return resp.data
