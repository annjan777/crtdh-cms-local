import pytest
from django.core.management import call_command
from apps.facilities.models import Equipment
from apps.media_gallery.models import MediaCoverageLink

@pytest.mark.django_db
def test_copy_fixes_change_only_exact_old_text():
    e = Equipment.objects.create(name="3d Printing Facilities")
    keep = Equipment.objects.create(name="3D printing (edited by hand)")
    call_command("apply_copy_fixes", "--dry-run")
    e.refresh_from_db(); assert e.name == "3d Printing Facilities"
    call_command("apply_copy_fixes")
    e.refresh_from_db(); keep.refresh_from_db()
    assert e.name == "3D printing facilities" and keep.name == "3D printing (edited by hand)"
    call_command("apply_copy_fixes")  # idempotent
    e.refresh_from_db(); assert e.name == "3D printing facilities"
