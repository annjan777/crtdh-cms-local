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

    # ---- Content refresh (audit IDs C-xx; see the remediation log). Only items that need no outside verification.
    # C-34 (supersedes C-02): hero statement on every slide that still carries the old line.
    ("carousel.HeroSlide", "description", 'Building affordable healthcare technology for a billion people, at IIT Kharagpur.',
     "Affordable healthcare technology research, development and translation at IIT Kharagpur."),
    # C-14 + C-15, merged so the second sentence does not repeat the first; the old population figure is dropped.
    ("core.HomePage", "objective_text", "Access to health is one of the fundamental rights enshrined in the constitution over the world. However, almost 50% of the world's 7.5 billion people is forced to live at underserved locations without access to basic healthcare and health education and public health measures, due to a multitude of reasons. This results in accumulation of diseases among the most vulnerable segment, delayed presentation and intervention, and consequent need of specialty treatment at high secondary and tertiary cost and health-related poverty shocks.",
     "Access to healthcare is a fundamental human right. Yet many communities continue to face barriers to basic "
     "healthcare, health education and preventive services. These barriers can delay diagnosis and treatment, "
     "increase the risk of complications and contribute to financial hardship."),
    # C-16
    ("core.HomePage", "membership_heading", 'Annual Membership for MSME / Startup', "Annual membership for MSMEs and startups"),
    # C-18 + C-19
    ("core.HomePage", "enterprises_text", 'One key area of focus of the CRTDH is supporting the growth and development of precision manufacturing of innovative medical devices through emerging micro-small-medium scale Industrial enterprises so that India can reduce their massive burden of imported healthcare technologies and spread the technology availability in the last-mile. The CRTDH has already established a template pilot plant to promote indigenously developed healthcare technologies for rural healthcare — solving a major problem for the common people, fostering manufacturing growth, creating rural jobs, and introducing advanced technologies into the ambit of public health.',
     "CRTDH supports MSMEs in developing and manufacturing affordable medical technologies. By helping enterprises "
     "build manufacturing capabilities, the Hub aims to improve access to indigenous healthcare technologies. "
     "CRTDH's pilot-plant facilities support the development and manufacturing of indigenous healthcare "
     "technologies. These capabilities aim to help innovators and enterprises translate research into solutions "
     "for healthcare delivery."),
    # C-20 + C-21 + C-22 (softer wording: claims reduced, nothing added)
    ("core.HomePage", "women_text_1", "The CRTDH & its implementation partner, FIH, has pioneered clusters of technology-enabled e-health clinics in remote villages where even primary healthcare centers do not function. This has fostered a silent socio-economic revolution where certified community health-workers deliver healthcare-support to last-mile populations. Large numbers of rural women have been trained to work as an interface between the patient, 'remote' doctor and the invented frugal diagnostic-technologies, enabling the establishment of their self-esteem and sustainable livelihood in the process.",
     "CRTDH, in collaboration with its implementation partner, FIH, has supported technology-enabled healthcare "
     "services in rural communities where access to healthcare facilities may be limited. The initiative supports "
     "community health workers in delivering healthcare services to underserved rural communities. Rural women have "
     "been trained to support patients and coordinate with remote healthcare professionals using affordable "
     "diagnostic technologies. The programme also aims to create opportunities for skills development and "
     "livelihoods."),
    # C-23 + C-24 (the claim about spurious medicines is removed: C-42)
    ("core.HomePage", "women_text_2", "Empowered by a 'primary-care software', this has led to all-in-one real-time data-driven clinical decision support system allowing for screening and risk-assessment of patients vetted by remote doctors to ensure high-quality evidence-based tailor-made advice. These centres make genuine medicines available to the rural population (where spurious medicines are sold in an unchecked manner), deliver basic physiotherapy services, undertake school & community-based health education and awareness activities; including manufacturing of simple health products such as Sanitizer, Face mask, Oral Rehydration Salts, Sanitary Napkins etc.",
     "The clinics use a primary-care software platform to support patient screening and risk assessment. Where "
     "applicable, remote healthcare professionals review the information and provide guidance. The centres may also "
     "provide access to medicines, basic physiotherapy, health education and community awareness activities. Some "
     "activities may include the production of essential health-related products, where applicable."),
    # C-25
    ("core.HomePage", "location_description", 'Available pilot plant and laboratories at CRTDH facility for research, MSME training and prototype development',
     "Pilot-plant and laboratory facilities at CRTDH support research, training and prototype development."),
    # C-06 and C-09 (C-07 and C-08 wait for verification)
    ("core.NewsItem", "text", 'CRTDH-supported Pathology and Eye Clinic — visit by the CRTDH team at Rural Healthcare Foundation',
     "CRTDH-supported pathology and eye clinic: visit to the Rural Healthcare Foundation"),
    ("core.NewsItem", "text", 'Health Awareness Programme and Conclave', "Health awareness programme and conclave"),
    # Redesign brief 26 Nov: the approved hero headline, one button, and a short institutional label (see C-33).
    ("carousel.HeroSlide", "heading", "Common Research &", "Affordable Healthcare."),
    ("carousel.HeroSlide", "highlight_heading", "Technology Development", "Engineered for Impact."),
    ("carousel.HeroSlide", "heading_end", "Hub", ""),
    ("carousel.HeroSlide", "eyebrow", "DSIR · GOVERNMENT OF INDIA", "CRTDH, IIT Kharagpur"),
    ("carousel.HeroSlide", "primary_button_label", "Explore Innovations", "See the technologies"),
    ("carousel.HeroSlide", "secondary_button_label", "About CRTDH", ""),
    ("core.NavItem", "label", "Contact Us", "Contact us"),
    # Review 25 Nov: the "Research translation" pathway now has its own page.
    ("core.HomePage", "pathway_2_link", "/enterprises", "/research-translation"),
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
