"""Page headers start with the wording the redesigned site shows, so editors see it in the CMS. No photos: until a
photo is chosen, each page keeps picking one of its own."""

from django.db import migrations

HEROES = [
    ("about", "About CRTDH", "About CRTDH",
     "A DSIR-sponsored initiative at IIT Kharagpur translating research in basic sciences, sensors and digital "
     "health into affordable, deployable healthcare technology."),
    ("team", "Team", "The people behind CRTDH",
     "Principal investigators, research members, project staff and medical collaborators."),
    ("innovations", "Innovations", "Our technology portfolio",
     "Medical devices, diagnostics and digital health tools developed at CRTDH for real-world, resource-constrained "
     "settings."),
    ("facilities", "Facilities", "Our facilities",
     "Instrumentation, pilot manufacturing and sterile facilities available to CRTDH researchers and partner "
     "enterprises."),
    ("services", "Services", "What CRTDH offers",
     "Testing, prototyping, certification support and technology transfer services for healthcare innovators."),
    ("product", "Product", "From prototype to product",
     "Flagship products developed and manufactured under CRTDH, along with our commercialisation partners."),
    ("enterprises", "Industry & MSMEs", "Collaborate with CRTDH",
     "The enterprise cluster CRTDH supports — from women-led rural livelihood ventures to medtech startups scaling "
     "manufacturing."),
    ("social-impact", "Social Impact", "Impact in rural India",
     "Health camps, rural clinics and outreach programmes bringing CRTDH innovations to the people who need them "
     "most."),
    ("covid-19", "Covid-19 Response", "CRTDH's response to the pandemic",
     "Diagnostics, PPE and community relief efforts undertaken by CRTDH during the Covid-19 pandemic."),
    ("media", "Media", "News & updates",
     "Photo galleries from CRTDH events, health camps and outreach programmes, plus press coverage."),
    ("contact", "Contact", "Get in touch",
     "Questions about our research, facilities, or partnering with CRTDH? Send us a message."),
    ("research", "Research", "Research at CRTDH",
     "Interdisciplinary research for affordable and deployable healthcare solutions."),
    ("research-translation", "Research translation", "From the lab to the field",
     "The journey from discovery to prototype, validation and translation."),
]


def seed(apps, schema_editor):
    PageHero = apps.get_model("common", "PageHero")
    for page, eyebrow, title, description in HEROES:
        PageHero.objects.get_or_create(page=page, defaults={"eyebrow": eyebrow, "title": title, "description": description})


def unseed(apps, schema_editor):
    PageHero = apps.get_model("common", "PageHero")
    for page, eyebrow, title, description in HEROES:
        PageHero.objects.filter(page=page, eyebrow=eyebrow, title=title, description=description, image="").delete()


class Migration(migrations.Migration):
    dependencies = [("common", "0006_impactfigure_pagehero_researchstory_and_more")]
    operations = [migrations.RunPython(seed, unseed)]
