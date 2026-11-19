"""Uploaded files are 0644 and folders 0755 whatever the SFTP server's umask (the web server is another user)."""
import os
import stat

import pytest

from .fakes import S1, S2, make_build, media_name


def publish(cms, pub, sid, pid, **kw):
    cms.queue(sid, pid, make_build(sid, pid, **kw))
    return pub.run_once()


def agent_written(home):
    """Every file and folder under the account's home that the agent wrote (not the pre-agent site's)."""
    for dirpath, dirnames, filenames in os.walk(home):
        rel = os.path.relpath(dirpath, home)
        if "legacy-" in rel or rel == "public_html" or rel.startswith("public_html" + os.sep + "images"):
            continue  # the fixture's old site (created by the test process, not over SFTP)
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            st = os.lstat(path)
            if stat.S_ISLNK(st.st_mode) or name.startswith("legacy-"):
                continue
            yield os.path.relpath(path, home), st


@pytest.mark.parametrize("strategy", ["symlink", "htaccess", "swap", "copy"])
def test_modes_ignore_a_077_umask(make_pub, cms, server, strategy):
    server.faults.umask = 0o077
    pub = make_pub(strategy=strategy)
    img = b"P" * 300
    assert publish(cms, pub, S1, "p1", media={media_name(img): img}) == "live"
    assert publish(cms, pub, S2, "p2", media_all=[media_name(img)]) == "live"
    seen = 0
    for rel, st in agent_written(server.home_path()):
        mode = stat.S_IMODE(st.st_mode)
        want = 0o755 if stat.S_ISDIR(st.st_mode) else 0o644
        assert mode == want, f"{rel}: {oct(mode)} (want {oct(want)})"
        seen += 1
    assert seen > 5


def test_umask_077_really_hides_files_without_chmod(make_pub, cms, server):
    """The fake applies the umask: a server that refuses chmod leaves 0600 files (and the agent says so)."""
    server.faults.umask = 0o077
    server.faults.no_chmod = True
    pub = make_pub()
    assert publish(cms, pub, S1, "p1") == "live"
    modes = {stat.S_IMODE(st.st_mode) for rel, st in agent_written(server.home_path())
             if not stat.S_ISDIR(st.st_mode)}
    assert modes == {0o600}
    with open(pub.cfg.log_file, encoding="utf-8") as fh:
        assert "refused to set file permissions" in fh.read()
