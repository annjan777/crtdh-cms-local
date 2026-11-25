"""One-off copy fixes for CMS text (typos, capitals on device names, raw URLs used as link titles).

Each fix changes a field only where it still holds exactly the old text, so running it twice, or after an
editor already fixed something by hand, changes nothing. --dry-run lists what would change.
Run it, then open Review & publish in the CMS and publish as usual.
"""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

# (app_label.Model, field, old, new)
FIXES = [
    ("facilities.Equipment", "name", "Two Sterile rooms BSL level 2", "Two sterile rooms (BSL-2)"),
    ("facilities.Equipment", "name", "Pilot Plant for Paper based Devices", "Pilot plant for paper-based devices"),
    ("facilities.Equipment", "name", "Electronic Dispenser", "Electronic dispenser"),
    ("facilities.Equipment", "name", "Vacuum Packaging Machine", "Vacuum packaging machine"),
    ("facilities.Equipment", "name", "Two Cryogenic Refrigerators (-80 & -20 degree)", "Two cryogenic refrigerators (−80 °C and −20 °C)"),
    ("facilities.Equipment", "name", "Wave Soldering Machine", "Wave soldering machine"),
    ("facilities.Equipment", "name", "Heat Chamber/ Autoclave", "Heat chamber / autoclave"),
    ("facilities.Equipment", "name", "High frequency (up to GHz) amplifier", "High-frequency (up to GHz) amplifier"),
    ("facilities.Equipment", "name", "Server and computer accessories", "Servers and computer accessories"),
    ("facilities.Equipment", "name", "Laser Cutter", "Laser cutter"),
    ("facilities.Equipment", "name", "Thermal Imaging System with IR Fusion Technology", "Thermal imaging system with IR fusion technology"),
    ("facilities.Equipment", "name", "Arbitrary Waveform Generator, DC Power Supply | Multimeter, Spectrum Analyzer",
     "Arbitrary waveform generator, DC power supply, multimeter and spectrum analyser"),
    ("facilities.Equipment", "name", "Covirap manufacturing unit", "COVIRAP manufacturing unit"),
    ("facilities.Equipment", "name", "Paper based device pilot plant", "Paper-based device pilot plant"),
    ("facilities.Equipment", "name", "Prototyping for PCB", "PCB prototyping"),
    ("facilities.Equipment", "name", "3d Printing Facilities", "3D printing facilities"),
    ("facilities.Equipment", "name", "Pathology Lab at Midnapur", "Pathology lab at Midnapur"),
    ("innovations.Innovation", "title", "Manufacturing Printed Paper Strips For Disease Detection", "Manufacturing Printed Paper Strips for Disease Detection"),
    ("innovations.Innovation", "title", "COVIRAP: A Nucleic-Acid Based Rapid Diagnostic Test for COVID-19", "COVIRAP: A Nucleic-Acid-Based Rapid Diagnostic Test for COVID-19"),
    ("innovations.Innovation", "title", "Clinical Algorithm based App for Delivering Primary Care at Resource Poor Settings-Uday",
     "Uday: Clinical Algorithm-Based App for Delivering Primary Care in Resource-Poor Settings"),
    ("innovations.Innovation", "title", "Covicube", "COVICUBE"),
    ("innovations.Innovation", "title", "Reagent-free Anemia screening using paper and smartphone", "Reagent-Free Anemia Screening Using Paper and a Smartphone"),
    ("innovations.Innovation", "title", "Hematocrit and Hemoglobin Measurement using EIS", "Hematocrit and Hemoglobin Measurement Using EIS"),
    ("enterprises.Enterprise", "name", "Softmed Technologies LLP.", "Softmed Technologies LLP"),
    ("enterprises.Enterprise", "name", "Foundation for Innovations in health", "Foundation for Innovations in Health"),
    ("enterprises.Enterprise", "name", "Inno-Dx solutions", "InnoDx Solutions"),
    ("enterprises.Enterprise", "name", "Sharobi technologies Pvt Ltd", "Sharobi Technologies Pvt Ltd"),
    ("enterprises.Enterprise", "name", "SPATIAL KARMA RESOURCES PVT. LTD.", "Spatial Karma Resources Pvt. Ltd."),
    ("services.Service", "title", "R & D support", "R&D support"),
    ("core.FocusArea", "title", "Medical Device and Diagnostics", "Medical Devices and Diagnostics"),
    ("core.TimelineEntry", "title", "Super Specialty Hospital", "Super Speciality Hospital"),
    ("common.ImageGridBlock", "section_title", "Demonstration And Training Of MSMEs", "Demonstration and training of MSMEs"),
    ("carousel.ProjectSlide", "title", "Smartphone based analysis", "Smartphone-based analysis"),
    ("media_gallery.GalleryImage", "caption", "CRTDH Supported Pathology Lab", "CRTDH-supported pathology lab"),
    ("media_gallery.GalleryImage", "caption", "Medical camp maintaining Covid Protocol", "Medical camp following Covid protocol"),
    ("media_gallery.GalleryImage", "caption", "CHW on a bicycle unit", "Community health worker on a bicycle unit"),
    # Press links whose title was the bare address: a readable title (publication and headline, from the address).
    ("media_gallery.MediaCoverageLink", "title",
     "https://www.thehindu.com/sci-tech/health/iit-kharagpur-launches-covirap-diagnostic-technology/article34376251.ece",
     "The Hindu: IIT Kharagpur launches COVIRAP diagnostic technology"),
    ("media_gallery.MediaCoverageLink", "title",
     "https://indianexpress.com/article/explained/covirap-iit-kharagpur-covid-test-explained-6830805/",
     "The Indian Express: COVIRAP, IIT Kharagpur's Covid test, explained"),
    ("media_gallery.MediaCoverageLink", "title",
     "https://www.telegraphindia.com/states/west-bengal/research-hub-at-iit-kharagpur-hospital/cid/1683564",
     "The Telegraph: Research hub at IIT Kharagpur hospital"),
    ("media_gallery.MediaCoverageLink", "title",
     "https://www.dnaindia.com/business/report-iit-kgp-to-set-up-hub-to-tap-msmes-for-affordable-healthcare-2715269",
     "DNA: IIT KGP to set up hub to tap MSMEs for affordable healthcare"),
    ("media_gallery.MediaCoverageLink", "title",
     "https://www.ndtv.com/education/iit-kharagpur-to-set-up-hub-to-tap-msmes-for-affordable-healthcare-1987360",
     "NDTV: IIT Kharagpur to set up hub to tap MSMEs for affordable healthcare"),
    ("media_gallery.MediaCoverageLink", "title",
     "https://yourstory.com/smbstory/iit-kharagpur-to-set-up-rd-hub-for-msmes-in-healthcare",
     "YourStory: IIT Kharagpur to set up R&D hub for MSMEs in healthcare"),
    ("media_gallery.MediaCoverageLink", "title",
     "http://www.uniindia.com/iit-to-set-up-msme-hub/east/news/1486337.html",
     "UNI: IIT to set up MSME hub"),
    ("media_gallery.MediaCoverageLink", "title",
     "http://pib.nic.in/PressReleseDetail.aspx?PRID=1562295",
     "PIB: Government press release"),
]


class Command(BaseCommand):
    help = "Apply the reviewed copy fixes (typos, device-name capitals, link titles) to CMS text."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="list the changes without saving")

    def handle(self, *args, dry_run=False, **opts):
        changed = 0
        with transaction.atomic():
            for label, field, old, new in FIXES:
                model = apps.get_model(label)
                for obj in model.objects.filter(**{field: old}):
                    self.stdout.write(f"{label}#{obj.pk}.{field}: {old!r} -> {new!r}")
                    if not dry_run:
                        setattr(obj, field, new)
                        obj.save()
                    changed += 1
            if dry_run:
                transaction.set_rollback(True)
        verb = "would change" if dry_run else "changed"
        self.stdout.write(self.style.SUCCESS(f"{verb} {changed} field(s)"))
