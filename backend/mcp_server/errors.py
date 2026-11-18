"""The MCP/CMS error contract (contracts §4, PLAN WS4.6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# code -> (default fix, retryable)
CODES: dict[str, tuple[str, bool]] = {
    "CMS_VALIDATION": ("Correct the field named in `field` and call the tool again.", False),
    "CMS_UNAUTHENTICATED": ("Ask the user to reconnect the CRTDH connector in Claude.", False),
    "CMS_FORBIDDEN_ROLE": ("Tell the user their CMS account can't do this; an Admin can check their role.", False),
    "CMS_NOT_FOUND": ("Call find_content or get_page to get a current id.", False),
    "CMS_STALE_VERSION": ("Call get_page for this page, then reapply the change with the new version.", False),
    "CMS_IMAGE_TOO_SMALL": ("Ask the user for a larger photo.", False),
    "CMS_FETCH_BLOCKED": ("Use request_upload_link so the user can upload the photo directly.", False),
    "CMS_RATE_LIMITED": ("Wait a minute, then try again.", True),
    "CMS_SESSION_LIMIT": (
        "Stop making changes. Ask the user to review them in the CMS, then start a new conversation.",
        False,
    ),
    "CMS_INTERNAL": (
        "Try once more. If it fails again, give the user this request id for the site admin.",
        True,
    ),
}


@dataclass
class CmsError(Exception):
    code: str
    message: str
    fix: str | None = None
    retryable: bool | None = None
    side_effects: str = "none"
    field: str | None = None
    current_version: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.code not in CODES:
            raise ValueError(f"unknown error code {self.code}")
        default_fix, default_retry = CODES[self.code]
        if self.fix is None:
            self.fix = default_fix
        if self.retryable is None:
            self.retryable = default_retry
        super().__init__(self.message)

    def to_dict(self, request_id: str) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "fix": self.fix,
            "retryable": self.retryable,
            "side_effects": self.side_effects,
            "request_id": request_id,
            "field": self.field,
            "current_version": self.current_version,
            **self.extra,
        }


def internal(request_id: str) -> CmsError:
    return CmsError(
        "CMS_INTERNAL",
        f"The CMS failed while handling this request (request id {request_id}).",
        side_effects="unknown — call list_pending_changes before retrying",
    )
