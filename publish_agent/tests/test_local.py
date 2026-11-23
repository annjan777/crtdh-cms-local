"""transport = local: the agent on the web server itself (deploy/academicweb), same publish steps as over SFTP."""
from publish_agent.strategies import HTACCESS_BEGIN, place_block

from .fakes import F1, F2, S1, S2, make_build


def publish(cms, pub, sid, pid, **kw):
    cms.queue(sid, pid, make_build(sid, pid, **kw))
    return pub.run_once()


HOST = "# BEGIN crtdh-host\nRewriteEngine On\nRewriteRule ^(cms|api)/ http://127.0.0.1:8650/$0 [P,L]\n# END crtdh-host\n"


def local_pub(make_pub, server):
    return make_pub(transport="local", sftp_host="", sftp_user="", key_file="",
                    web_root=server.home_path("public_html"), strategy="htaccess")


def test_local_publish_keeps_the_host_block_first_and_the_old_files(make_pub, cms, server):
    ht = server.home_path("public_html", ".htaccess")
    with open(ht, "w") as fh:
        fh.write(HOST + "# a line the owner added\n")
    pub = local_pub(make_pub, server)
    assert publish(cms, pub, S1, "p1") == "live"
    text = open(ht).read()
    assert text.startswith(HOST)  # the host's forwarding rules stay above the agent's catch-all
    assert text.index("# END crtdh-host") < text.index(HTACCESS_BEGIN)
    assert f"# Live release: {F1}." in text and "# a line the owner added" in text
    assert open(server.home_path("public_html", "images", "logo.png"), "rb").read() == b"PNGDATA"

    assert publish(cms, pub, S2, "p2") == "live"
    text = open(ht).read()
    assert text.startswith(HOST) and text.count(HTACCESS_BEGIN) == 1 and f"# Live release: {F2}." in text


def test_place_block():
    block = f"{HTACCESS_BEGIN}\nX\n# END crtdh-publish-agent\n"
    assert place_block("", block) == block
    assert place_block("Other\n", block) == block + "Other\n"
    assert place_block(HOST + "Other\n", block) == HOST + block + "Other\n"
    old = f"{HTACCESS_BEGIN}\nOLD\n# END crtdh-publish-agent\n"
    assert place_block("A\n" + old + "B\n", block) == "A\n" + block + "B\n"  # replaced in place
