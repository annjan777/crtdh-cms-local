import os

from .fakes import make_build, media_name


def test_happy_path_symlink(make_pub, cms, server):
    img = b"IMG1" * 100
    m = media_name(img)
    cms.queue("snap-1", "p1", make_build("snap-1", "p1", media={m: img}))
    pub = make_pub()
    assert pub.run_once() == "live"
    assert cms.last("p1")["status"] == "live"
    wr = server.home_path("public_html")
    assert os.path.islink(wr)
    assert "home snap-1" in open(os.path.join(wr, "index.html")).read()
    assert open(os.path.join(wr, "media", m), "rb").read() == img
