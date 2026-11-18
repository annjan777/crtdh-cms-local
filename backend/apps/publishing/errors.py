"""Contract §4 error body.

backend-security owns the canonical handler (apps.common.errors, same API as below). When it is present (after
the lanes merge) this module re-exports it; otherwise the local fallback below is used. Contract addendum A4
extras (edited_by, publish_id, details, ...) are added with `with_extra()`, which works with either.
"""
try:  # pragma: no cover - exercised after merge
    from apps.common.errors import (  # noqa: F401
        DEFAULT_FIX,
        STATUS,
        CMSError,
        _validation_message,
        as_error_body,
        error_body,
        error_response,
        exception_handler,
        new_request_id,
    )
except ImportError:
    from ._errors_fallback import (  # noqa: F401
        DEFAULT_FIX,
        STATUS,
        CMSError,
        _validation_message,
        as_error_body,
        error_body,
        error_response,
        exception_handler,
        new_request_id,
    )


def with_extra(exc, **extra):
    """Attach addendum-A4 keys to a CMSError's body and return it (raise with_extra(CMSError(...), k=v))."""
    exc.body.update(extra)
    return exc
