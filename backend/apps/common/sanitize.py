"""One allow-list for rich text and one rule for links, applied on every write path (see apps.publishing.apps).

- clean_richtext(html): p, br, strong/b, em/i, a[href, rel=noopener], ul, ol, li, h3. Everything else is stripped;
  hrefs must pass safe_url().
- safe_url(value): http(s)://, mailto:, tel:, site-relative (/page, #anchor, page). Refuses protocol-relative
  //host (and /\\host), javascript:, data:, vbscript: and any other scheme, also when hidden by whitespace,
  control characters or entities.
"""
import html
import re

import bleach
from bleach.html5lib_shim import Filter

TAGS = ["p", "br", "strong", "b", "em", "i", "a", "ul", "ol", "li", "h3"]
SCHEMES = {"http", "https", "mailto", "tel"}
_SCHEME = re.compile(r"^([a-z][a-z0-9+.\-]*):")
_INVISIBLE = re.compile("[\\x00-\\x20\\x7f-\\x9f\\u200b-\\u200f\\u2028\\u2029\\ufeff]")


def safe_url(value):
    """True if `value` is a link the public site may carry (empty is fine)."""
    if value is None:
        return True
    s = str(value)
    if not s.strip():
        return True
    squashed = _INVISIBLE.sub("", html.unescape(s)).lower()
    if squashed.startswith(("//", "/\\", "\\\\", "\\/")):
        return False
    m = _SCHEME.match(squashed)
    if m:
        return m.group(1) in SCHEMES
    return ":" not in squashed.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]


def _href_ok(tag, name, value):
    if tag == "a" and name == "href":
        return safe_url(value)
    return tag == "a" and name == "rel"


class _NoOpener(Filter):
    def __iter__(self):
        for token in super().__iter__():
            if token.get("type") in ("StartTag", "EmptyTag") and token.get("name") == "a":
                data = dict(token.get("data") or {})
                data[(None, "rel")] = "noopener"
                token["data"] = data
            yield token


_cleaner = bleach.Cleaner(tags=TAGS, attributes={"a": _href_ok}, protocols=list(SCHEMES), strip=True,
                          strip_comments=True, filters=[_NoOpener])


def clean_richtext(value):
    """Plain text without any '<' is returned unchanged (cleaning would turn "R&D" into "R&amp;D" for fields the
    public site still renders as text); anything with markup goes through the allow-list."""
    if not value or "<" not in str(value):
        return value
    return _cleaner.clean(str(value))
