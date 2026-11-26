import pytest
from django.core.management import call_command
from apps.facilities.models import Equipment

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


@pytest.mark.django_db
def test_refinement_copy_matches_staging_text_and_never_overwrites_editor_text():
    from apps.core.management.commands import _refinement_copy as rc
    from apps.core.models import AboutPage
    from apps.innovations.models import Innovation
    from apps.products.models import Product
    from apps.services.models import Service

    about = AboutPage.objects.create(mission_vision=rc._MISSION_OLD, intro=f"{rc._INTRO_P1}\n\n{rc._INTRO_OLD_P2}")
    olds = [rc._ORAL_OLD, rc._CHEST_OLD, rc._COVIRAP_OLD, rc._LIPID_OLD, rc._DISC_OLD, rc._UDAY_OLD, rc._HB_OLD, rc._GLUCO_OLD]
    inns = [Innovation.objects.create(title=f"t{k}", body=b) for k, b in enumerate(olds)]
    tail = "<li>Open smartphone app.</li></ol>"
    anemia = Innovation.objects.create(title="anemia", body=rc._ANEMIA_OLD + tail)
    svc = Service.objects.create(title="R&D support")
    edited = Service.objects.create(title="Regulatory guidance", description="Written by an editor.")
    prod = Product.objects.create(name="Sense-Hb")

    call_command("apply_copy_fixes")
    about.refresh_from_db()
    assert about.mission_vision == rc._MISSION_NEW and "18 CRTDHs" not in about.intro
    news = [rc._ORAL_NEW, rc._CHEST_NEW, rc._COVIRAP_NEW, rc._LIPID_NEW, rc._DISC_NEW, rc._UDAY_NEW, rc._HB_NEW, rc._GLUCO_NEW]
    for inn, new in zip(inns, news):
        inn.refresh_from_db(); assert inn.body.startswith(new[:80]) and inn.body.endswith(new[-6:])
    anemia.refresh_from_db()
    assert anemia.body.startswith(rc._ANEMIA_NEW[:80]) and "Test procedure" in anemia.body and anemia.body.endswith(tail)
    svc.refresh_from_db(); edited.refresh_from_db(); prod.refresh_from_db()
    assert svc.description.startswith("Research and development") and "Patenting support" in svc.includes
    assert edited.description == "Written by an editor."
    assert prod.status == "licensed" and "10 µL" in prod.summary

    call_command("apply_copy_fixes")  # a second run changes nothing
    anemia.refresh_from_db()
    assert anemia.body.count("Test procedure") == 1
