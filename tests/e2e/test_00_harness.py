"""Harness self-checks: runnable today, before integration."""
import urllib.request


def test_backend_up_with_prod_like_settings(stack):
    try:
        urllib.request.urlopen(f"{stack.api}/api/v1/auth/me/", timeout=5)
        raise AssertionError("anonymous /auth/me/ must not be 200")
    except urllib.error.HTTPError as e:
        assert e.code in (401, 403)


def test_seeded_users(stack):
    if stack.users:
        assert {u["role"] for u in stack.users.values()} == {"editor", "publisher", "admin"}


def test_static_host_404(tmp_path):
    import threading

    from tools.static_server import serve
    (tmp_path / "index.html").write_text("<h1>home</h1>")
    (tmp_path / "about").mkdir()
    (tmp_path / "about" / "index.html").write_text("<h1>about</h1>")
    (tmp_path / "404.html").write_text("<h1>Page not found</h1>")
    srv = serve(tmp_path, 3609)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        assert b"about" in urllib.request.urlopen("http://localhost:3609/about").read()
        try:
            urllib.request.urlopen("http://localhost:3609/nope")
        except urllib.error.HTTPError as e:
            assert e.code == 404 and b"Page not found" in e.read()
        req = urllib.request.Request("http://localhost:3609/", data=b"x", method="POST")
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            assert e.code == 405
    finally:
        srv.shutdown()


def test_browser_launches(page):
    page.set_content("<main><h1>ok</h1></main>")
    assert page.inner_text("h1") == "ok"


def test_stack_never_prints_test_secrets(stack):
    """R-9 / F-09: pytest prints fixtures in tracebacks; the stack's repr must not carry TOTP seeds or the password."""
    text = repr(stack) + str(stack)
    assert "totp" not in text.lower()
    assert stack.password not in text
    for user in stack.users.values():
        secret = (user or {}).get("totp_secret")
        if secret:
            assert secret not in text
