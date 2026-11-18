"""Assertions for the contract §4 error body (API responses and MCP structuredContent)."""
import json
import re

STATUS_FOR_CODE = {
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
REQUIRED_KEYS = {"code", "message", "fix", "retryable", "side_effects", "request_id"}
OPTIONAL_KEYS = {"field", "current_version"}

# Things that must never leak into an error (contract §4).
LEAK_PATTERNS = [
    r"Traceback \(most recent call last\)",
    r'File "[^"]+\.py", line \d+',
    r"django\.(db|core)\.[a-z_.]+Error",
    r"(?i)\bsecret[_-]?key\b",
    r"(?i)password\s*[=:]",
    r"(?i)bearer\s+[A-Za-z0-9._-]{16,}",
    r"(?i)[?&](signature|token|X-Amz-Signature|sig)=",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]


def _body(resp_or_dict):
    if isinstance(resp_or_dict, dict):
        return resp_or_dict
    data = getattr(resp_or_dict, "data", None)
    if isinstance(data, dict):
        return data
    return json.loads(resp_or_dict.content or b"{}")


def assert_no_leak(text):
    text = text if isinstance(text, str) else json.dumps(text, default=str)
    for pat in LEAK_PATTERNS:
        assert not re.search(pat, text), f"error body leaks something matching {pat!r}: {text[:300]}"


def assert_contract_error(resp_or_dict, code, *, status=None, field=None, current_version=None, retryable=None):
    """Assert a contract §4 error. Works on a DRF/Django response or an MCP structuredContent dict.

    Returns the body so callers can make extra assertions (e.g. the editor's name in the message).
    """
    if not isinstance(resp_or_dict, dict):
        expected = status if status is not None else STATUS_FOR_CODE[code]
        assert resp_or_dict.status_code == expected, (
            f"expected HTTP {expected} for {code}, got {resp_or_dict.status_code}: {getattr(resp_or_dict, 'content', b'')[:300]!r}"
        )
    body = _body(resp_or_dict)
    missing = REQUIRED_KEYS - body.keys()
    assert not missing, f"error body missing {sorted(missing)}: {body}"
    extra = body.keys() - REQUIRED_KEYS - OPTIONAL_KEYS
    assert not extra, f"error body has non-contract keys {sorted(extra)}"
    assert body["code"] == code, f"expected code {code}, got {body['code']}: {body.get('message')}"
    assert isinstance(body["message"], str) and body["message"].strip()
    assert isinstance(body["fix"], str) and body["fix"].strip()
    assert isinstance(body["retryable"], bool)
    assert isinstance(body["side_effects"], str)
    assert body["request_id"], "request_id must be set"
    if field is not None:
        assert body.get("field") == field
    if current_version is not None:
        assert body.get("current_version") == current_version
    if retryable is not None:
        assert body["retryable"] is retryable
    assert_no_leak(body)
    return body
