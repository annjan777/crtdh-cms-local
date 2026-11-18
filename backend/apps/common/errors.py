"""Contract §4 error bodies for every API response.

Raise `CMSError(code, message, fix=..., status=...)` from any view; DRF's own
exceptions are mapped by `exception_handler`. Bodies never carry secrets,
tokens, signed URLs or tracebacks.
"""
import logging

from django.http import JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response

logger = logging.getLogger("crtdh.security")

STATUS_BY_CODE = {
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


class CMSError(exceptions.APIException):
    def __init__(self, code, message, *, fix="", retryable=False, side_effects="none",
                 field=None, current_version=None, status_code=None, extra=None, headers=None):
        self.status_code = status_code or STATUS_BY_CODE.get(code, 400)
        self.code = code
        self.body = {
            "code": code,
            "message": message,
            "fix": fix,
            "retryable": retryable,
            "side_effects": side_effects,
            "field": field,
            "current_version": current_version,
        }
        if extra:
            self.body.update(extra)
        self.headers = headers or {}
        super().__init__(detail=message, code=code)


def _body(request, code, message, fix="", **kw):
    body = {"code": code, "message": message, "fix": fix, "retryable": False,
            "side_effects": "none", "field": None, "current_version": None}
    body.update(kw)
    body["request_id"] = getattr(request, "request_id", None)
    return body


def _first_field(detail):
    if isinstance(detail, dict):
        for key, val in detail.items():
            sub = _first_field(val)
            return (key if key != "non_field_errors" else None), (sub[1] if sub else str(val))
    if isinstance(detail, list) and detail:
        return _first_field(detail[0])
    return None, str(detail)


def exception_handler(exc, context):
    request = context.get("request")
    if isinstance(exc, CMSError):
        body = dict(exc.body, request_id=getattr(request, "request_id", None))
        return Response(body, status=exc.status_code, headers=exc.headers)

    if isinstance(exc, exceptions.ValidationError):
        field, msg = _first_field(exc.detail)
        return Response(
            _body(request, "CMS_VALIDATION", msg, "Correct the highlighted field and try again.",
                  field=field),
            status=400,
        )
    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        return Response(_body(request, "CMS_UNAUTHENTICATED", "Sign in to continue.", "Sign in again."),
                        status=401, headers={"WWW-Authenticate": "Session"})
    if isinstance(exc, exceptions.PermissionDenied):
        detail = str(exc.detail)
        if detail.startswith("CSRF Failed"):
            return Response(_body(request, "CMS_CSRF_FAILED", "Security token missing or expired.",
                                  "Fetch /api/v1/auth/csrf/ and resend with the X-CSRFToken header.",
                                  retryable=True), status=403)
        return Response(_body(request, "CMS_FORBIDDEN_ROLE", "Your role does not allow this action.",
                              "Ask an admin for the right role."), status=403)
    if isinstance(exc, exceptions.NotFound):
        return Response(_body(request, "CMS_NOT_FOUND", "Not found.", "Check the id and try again."), status=404)
    if isinstance(exc, exceptions.Throttled):
        wait = int(exc.wait or 60)
        return Response(_body(request, "CMS_RATE_LIMITED", f"Too many requests. Try again in {wait} seconds.",
                              "Wait and retry.", retryable=True),
                        status=429, headers={"Retry-After": str(wait)})
    if isinstance(exc, exceptions.APIException):
        # MethodNotAllowed, ParseError, UnsupportedMediaType, NotAcceptable ...
        return Response(_body(request, "CMS_VALIDATION", str(exc.detail), "Check the request format."),
                        status=exc.status_code)
    from django.http import Http404
    from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
    if isinstance(exc, Http404):
        return Response(_body(request, "CMS_NOT_FOUND", "Not found.", "Check the id and try again."), status=404)
    if isinstance(exc, DjangoPermissionDenied):
        return Response(_body(request, "CMS_FORBIDDEN_ROLE", "Your role does not allow this action.",
                              "Ask an admin for the right role."), status=403)

    logger.exception("unhandled API error request_id=%s", getattr(request, "request_id", None))
    return Response(_body(request, "CMS_INTERNAL", "Something went wrong on our side.",
                          "Try again; if it keeps failing, report the request id.", retryable=True),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def csrf_failure(request, reason=""):
    """Django-level CSRF failures (non-DRF views) get the same JSON body."""
    return JsonResponse(
        _body(request, "CMS_CSRF_FAILED", "Security token missing or expired.",
              "Fetch /api/v1/auth/csrf/ and resend with the X-CSRFToken header.", retryable=True),
        status=403,
    )
