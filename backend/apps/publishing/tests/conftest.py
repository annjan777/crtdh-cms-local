"""backend-core fixtures (root fixtures come from backend/conftest.py, owned by qa)."""
import sys
from pathlib import Path

import pytest

FAKE_BUILD = Path(__file__).with_name("fake_build.py")
SECRET = "test-agent-secret-not-real"


@pytest.fixture
def content(sample_content):
    return sample_content


@pytest.fixture
def ctx(editor):
    from apps.publishing.audit import WriteContext
    return WriteContext(user=editor, channel="admin")


@pytest.fixture
def publish_env(settings, tmp_path, media_root):
    """Isolated PUBLISH_ROOT, a fake frontend build, and an agent secret."""
    settings.PUBLISH_ROOT = str(tmp_path / "publish")
    settings.FRONTEND_BUILD_OUTPUT = str(tmp_path / "frontend-out")
    settings.FRONTEND_BUILD_CMD = f"{sys.executable} {FAKE_BUILD}"
    settings.AGENT_HMAC_SECRET = SECRET
    return tmp_path


@pytest.fixture
def baseline(db, content):
    """Publish today's sample content as the live baseline."""
    from django.core.management import call_command
    call_command("create_baseline_snapshot", stdout=open("/dev/null", "w"))
    from apps.publishing.models import Snapshot
    return Snapshot.last_published()


def image_file(path, width=2000, height=1000, color=(15, 76, 117)):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (width, height), color).save(path, format="JPEG", quality=85)
    return path
