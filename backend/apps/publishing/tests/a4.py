"""Addendum A4 error extras on top of qa's contract §4 assertion (tests/support/errors.py lists only §4 keys)."""
from tests.support.errors import _body, assert_contract_error

A4_EXTRAS = {"CMS_STALE_VERSION": {"edited_by", "edited_at"}, "CMS_PUBLISH_RUNNING": {"publish_id"},
             "CMS_BUILD_GUARD": {"details"}}


def assert_a4_error(resp, code, **kw):
    """Check the A4 extras exist for `code`, then run the §4 check on the body without them. Returns the full body."""
    body = dict(_body(resp))
    extras = A4_EXTRAS.get(code, set())
    assert extras <= body.keys(), f"{code} body lacks addendum A4 keys {sorted(extras - body.keys())}: {body}"
    core = {k: v for k, v in body.items() if k not in extras}
    if not isinstance(resp, dict):
        expected = kw.pop("status", None)
        from tests.support.errors import STATUS_FOR_CODE
        assert resp.status_code == (expected or STATUS_FOR_CODE[code]), resp.content[:300]
    assert_contract_error(core, code, **kw)
    return body
