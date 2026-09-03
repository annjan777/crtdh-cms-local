"""Fills in the content that seed_from_mirror never captured: About page
prose/focus areas/objectives/timeline, the IIT KGP + DSIR header logos, and
the Social Impact / Covid-19 image + video galleries. All hand-authored
from the original mirror at MIRROR_ROOT (about.html, social-impact.html,
covid-19.html) rather than auto-parsed, since these sections aren't
uniform repeating markup. Idempotent: safe to re-run (clears and re-creates
each section it owns) — every image/file save goes through _save_file()
below so a re-run always converges on the same on-disk filename instead of
leaking a Django-suffixed duplicate (foo_XXXXXXX.jpg) each time.
"""

import os
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from apps.common.models import ImageGridBlock, ImageGridItem, VideoBlock
from apps.core.models import AboutPage, FocusArea, HomePage, ObjectiveRow, SiteSettings, TimelineEntry

MIRROR_ROOT = Path("/home/claude/crtdh_mirror/site/images")


def _file(rel_path):
    path = MIRROR_ROOT / rel_path
    if not path.exists():
        return None
    return File(open(path, "rb"), name=path.name)


def _save_file(field_file, filename, file_obj):
    """Idempotent replacement for `field_file.save(filename, file_obj,
    save=False)`. Plain `.save()` never overwrites — if a file already
    sits at the target path (from a previous run of this command),
    Django's storage backend mangles the name (foo_XXXXXXX.jpg) instead,
    so re-running this command repeatedly leaks a growing pile of
    duplicate files. This deletes whatever the field currently points to
    plus anything already sitting at the canonical target path first, so
    every re-run converges on the same filename."""
    storage = field_file.storage
    if field_file.name and storage.exists(field_file.name):
        storage.delete(field_file.name)
    target = os.path.join(str(field_file.field.upload_to), filename)
    if storage.exists(target):
        storage.delete(target)
    field_file.save(filename, file_obj, save=False)


class Command(BaseCommand):
    help = "Seed About page, header logos, Social Impact and Covid-19 content (hand-authored from the mirror)."

    def handle(self, *args, **options):
        self._site_logos()
        self._about_page()
        self._focus_areas()
        self._objectives()
        self._timeline()
        self._social_impact()
        self._covid19()
        self._home_page()
        self.stdout.write(self.style.SUCCESS("Content gaps seeded."))

    def _site_logos(self):
        settings_obj = SiteSettings.load()
        left = _file("logo/iit-kgp-logo.png")
        right = _file("logo/dsir-logo.png")
        mark = _file("logo/CRTDH-LOGO.png")
        if left:
            _save_file(settings_obj.logo_left, "iit-kgp-logo.png", left)
        if right:
            _save_file(settings_obj.logo_right, "dsir-logo.png", right)
        if mark:
            _save_file(settings_obj.site_logo, "CRTDH-LOGO.png", mark)
        if not settings_obj.map_embed_url:
            settings_obj.map_embed_url = (
                "https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d14764.096494212994!2d87.3105311"
                "!3d22.3149274!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3a1d440255555547%3A0x6f2f20dd0c0d6793"
                "!2sIndian%20Institute%20of%20Technology%20Kharagpur!5e0!3m2!1sen!2sin!4v1689086915720!5m2!1sen!2sin"
            )
        settings_obj.save()
        self.stdout.write("Site logos set.")

    def _about_page(self):
        about = AboutPage.load()
        about.intro = (
            "Innovation plays a critical role in shaping the industrial competitiveness of any nation. "
            "India, being a developing nation, has its own set of unique situations and challenges that "
            "impede the innovation potential of MSMEs operating in it. Many of these challenges are related "
            "to public policy, funding constraints, access to suitable equipment, shortage of skilled R&D "
            "workforce and weak linkages between institutions and industry. DSIR has therefore initiated a "
            "program aimed at the creation of Common Research & Technology Development Hubs (CRTDHs) to "
            "encourage research and technology development by MSMEs and develop synergy between academia "
            "and industry, facilitating hands-on training, skill development and R&D infrastructure.\n\n"
            "DSIR-CRTDH is now a strong family of 18 CRTDHs located across the country, working in sectors "
            "such as electronics/renewable energy, affordable health, environmental interventions, low-cost "
            "machining and new materials/chemical processes — all engaged in R&D activity with real societal "
            "impact, helping MSMEs remain competitive while DSIR expands the network across every state and "
            "Union Territory."
        )
        about.mission_vision = (
            "Almost half of the world's population is forced to live without access to basic healthcare, "
            "health education and public health measures — a cycle that pushes millions below the poverty "
            "line every year through health-related expenses. Breaking that cycle means intermingling "
            "advances in healthcare technology, including digital healthcare, with value-added human "
            "resource development — the central principle behind CRTDH's vision at IIT Kharagpur.\n\n"
            "The CRTDH for Affordable Health at IIT Kharagpur was established in 2019 to support MSMEs, "
            "startups and entrepreneurs working in the healthcare domain, offering R&D support, "
            "state-of-the-art facilities, a manufacturing plant and licensing support. In spite of the "
            "constraints of the COVID-19 pandemic, CRTDH developed several point-of-care technologies, "
            "trained community health workers, ran medical and validation camps in remote settings, and set "
            "up a Pathology and Imaging Lab in collaboration with an NGO — continuing to make healthcare "
            "accessible to the last-mile population."
        )
        about.focus_intro = (
            "Affordable healthcare for a billion people\nDiligence in Basic Sciences and Mathematical Modelling"
        )
        about.ecosystem_heading = "An Advanced Institute of Medical Science and Research"
        eco = _file("eco-system.jpg")
        if eco:
            _save_file(about.ecosystem_image, "eco-system.jpg", eco)
        pi = _file("from-pi-desk.jpg")
        if pi:
            _save_file(about.pi_desk_image, "from-pi-desk.jpg", pi)
        about.dsir_about = (
            "The Department of Scientific and Industrial Research (DSIR) is part of the Ministry of Science "
            "and Technology, established through a Presidential Notification dated January 4, 1985, under the "
            "164th Amendment of the Government of India (Allocation of Business) Rules, 1961. DSIR carries "
            "out activities relating to indigenous technology promotion, development, utilisation and "
            "transfer.\n\nIts primary endeavour is to promote R&D by industry, support small and medium "
            "industrial units in developing globally competitive technologies, catalyse faster "
            "commercialisation of lab-scale R&D, and strengthen industrial consultancy and technology "
            "management capabilities — linking scientific laboratories with industrial establishments "
            "through the National Research Development Corporation (NRDC) and facilitating R&D investment "
            "through Central Electronics Limited (CEL). dsir.gov.in"
        )
        about.iitkgp_about = (
            "The Indian Institute of Technology Kharagpur (IIT Kharagpur) is a public institute of technology "
            "and research university established by the Government of India in Kharagpur, West Bengal. "
            "Established in 1951, it is the first of the IITs and is recognised as an Institute of National "
            "Importance."
        )
        about.save()
        self.stdout.write("About page prose set.")

    def _focus_areas(self):
        FocusArea.objects.all().delete()
        blocks = [
            ("Medical Device and Diagnostics", "#520000"),
            ("Sensors & Materials for Healthcare", "#005521"),
            ("System Modeling", "#001455"),
            ("Technology for Healthcare", "#2c0055"),
            ("Understanding the Science of Human Health", "#2b2a2a"),
            ("Digital Convergence in Medical Technology", "#4c5500"),
            ("Interconnection of Biosystems", "#004b55"),
        ]
        for i, (title, color) in enumerate(blocks):
            FocusArea.objects.create(title=title, color=color, order=i)
        self.stdout.write(f"Seeded {len(blocks)} focus areas.")

    def _objectives(self):
        ObjectiveRow.objects.all().delete()
        rows = [
            ("Ideation", "MSMEs state their ideas about new products/services based on their understanding of market needs", "Builds two-way traffic for idea-sharing and more relevant products"),
            ("Ideation", "MSMEs state their ideas about new products/services based on their understanding of market needs", "Selection of product/device/service"),
            ("Capacity-building", "Hands-on training to MSMEs for prototype development using CRTDH facilities", "Addresses the key challenge of 'Training & R&D Capability' for MSMEs"),
            ("Capacity-building", "Imparting fundamental knowledge to MSMEs about the technology platform of the device/service and how it works", ""),
            ("Key risks mitigation", "Provide access to rural healthcare network and super-speciality hospitals for initial validation study of the device/service", "Addresses the challenge faced by MSMEs towards investment in risky early-stage development"),
            ("Key risks mitigation", "Patenting support", ""),
            ("Key risks mitigation", "Data analysis and iterative development for MSMEs", ""),
            ("Key risks mitigation", "Develop product to 'Design-for-Manufacture' stage", ""),
            ("Trial and final validation", "Create access for MSMEs to multi-centric trials with appropriate IRB clearances", "Provides a knowledge base for conducting validated trials and data analysis"),
            ("Trial and final validation", "Data analysis and validation", ""),
            ("Technology transfer", "Transfer technologies to MSMEs through appropriate agreements on royalty share", ""),
            ("Certification", "Assist MSMEs through the certification process", "Assistance in regulatory clearances"),
            ("Certification", "CDSCO, DCGI, CE, European CE, ISI, BIS (as appropriate)", ""),
            ("Initial market access", "Provide immediate sale support to MSMEs via access to IIT Kharagpur's rural healthcare network, building initial confidence and success stories", "Initial sale and revenue stream creation"),
        ]
        for i, (category, task, outcome) in enumerate(rows):
            ObjectiveRow.objects.create(category=category, task=task, outcome=outcome, order=i)
        self.stdout.write(f"Seeded {len(rows)} objective rows.")

    def _timeline(self):
        TimelineEntry.objects.all().delete()
        entries = [
            ("2001", "School of Medical Science and Technology", "2001.jpg"),
            ("2013-14", "Signals and Systems for Life Science", "2013-14.jpg"),
            ("2021", "Super Specialty Hospital", "2021.jpg"),
        ]
        for i, (year, title, filename) in enumerate(entries):
            entry = TimelineEntry(year=year, title=title, order=i)
            f = _file(filename)
            if f:
                _save_file(entry.image, filename, f)
            entry.save()
        self.stdout.write(f"Seeded {len(entries)} timeline entries.")

    def _image_grid(self, page, section_title, intro, filenames, subdir):
        ImageGridBlock.objects.filter(page=page).delete()
        block = ImageGridBlock.objects.create(page=page, section_title=section_title, intro=intro)
        count = 0
        for i, filename in enumerate(filenames):
            f = _file(f"{subdir}/{filename}")
            if not f:
                continue
            item = ImageGridItem(block=block, order=i)
            # Different pages' source filenames collide (both social-impact
            # and covid-19 have their own "01.jpg" etc.) and all
            # ImageGridItems share the same upload_to="image_grid_items/"
            # directory, so the on-disk name is namespaced by page here —
            # otherwise _save_file's dedup would have one page's seed step
            # silently delete and replace another page's same-named file.
            target_name = f"{subdir}-{filename}"
            _save_file(item.image, target_name, f)
            item.save()
            count += 1
        self.stdout.write(f"Seeded {count} images for '{page}'.")

    def _social_impact(self):
        filenames = [
            "01.jpg", "02.jpg", "03.jpg", "04.jpg", "05.png", "06.png",
            "07.png", "08.JPG", "09.JPG", "10.JPG", "11.jpg", "12.jpg",
        ]
        self._image_grid(
            "social-impact",
            "Community outreach",
            "Health camps, rural clinics and outreach programmes bringing CRTDH innovations to the people who need them most.",
            filenames,
            "social-impact",
        )

    def _covid19(self):
        filenames = ["01.jpg", "02.jpg", "03.jpg", "04.jpg"]
        self._image_grid(
            "covid-19",
            "Combating the pandemic",
            "In response to COVID-19, the CRTDH team developed PINAT — a piece-wise isothermal nucleic acid "
            "test platform for diagnosing pathogen-associated infections — an ultra-low-cost, accurate "
            "point-of-care nucleic acid test with the simplicity of a common rapid test. CRTDH also trained "
            "community health workers to prepare masks and sanitisers and ran medical/validation camps in "
            "remote settings during the pandemic.",
            filenames,
            "covid-19",
        )
        VideoBlock.objects.filter(page="covid-19").delete()
        for i, yt_id in enumerate(["ZkZXzuaIeoQ", "0adKih1-0Ms"]):
            VideoBlock.objects.create(
                page="covid-19",
                title="CRTDH Covid-19 response" if i == 0 else "PINAT diagnostic platform",
                youtube_url=f"https://www.youtube.com/watch?v={yt_id}",
                order=i,
            )
        self.stdout.write("Seeded 2 covid-19 videos.")

    def _home_page(self):
        home = HomePage.load()
        home.objective_text = (
            "Access to health is one of the fundamental rights enshrined in the constitution over the world. "
            "However, almost 50% of the world's 7.5 billion people is forced to live at underserved locations "
            "without access to basic healthcare and health education and public health measures, due to a "
            "multitude of reasons. This results in accumulation of diseases among the most vulnerable segment, "
            "delayed presentation and intervention, and consequent need of specialty treatment at high "
            "secondary and tertiary cost and health-related poverty shocks."
        )

        home.enterprises_text = (
            "One key area of focus of the CRTDH is supporting the growth and development of precision "
            "manufacturing of innovative medical devices through emerging micro-small-medium scale Industrial "
            "enterprises so that India can reduce their massive burden of imported healthcare technologies and "
            "spread the technology availability in the last-mile. The CRTDH has already established a template "
            "pilot plant to promote indigenously developed healthcare technologies for rural healthcare — "
            "solving a major problem for the common people, fostering manufacturing growth, creating rural "
            "jobs, and introducing advanced technologies into the ambit of public health."
        )
        e1 = _file("enterprises-engagement01.jpg")
        if e1:
            _save_file(home.enterprises_image_1, "enterprises-engagement01.jpg", e1)
        e2 = _file("enterprises-engagement02.JPG")
        if e2:
            _save_file(home.enterprises_image_2, "enterprises-engagement02.jpg", e2)
        msme = _file("msmemap.png")
        if msme:
            _save_file(home.msme_map_image, "msmemap.png", msme)
        home.msme_caption = "MSME cluster supported by CRTDH, IIT KGP"

        home.women_text_1 = (
            "The CRTDH & its implementation partner, FIH, has pioneered clusters of technology-enabled "
            "e-health clinics in remote villages where even primary healthcare centers do not function. This "
            "has fostered a silent socio-economic revolution where certified community health-workers deliver "
            "healthcare-support to last-mile populations. Large numbers of rural women have been trained to "
            "work as an interface between the patient, 'remote' doctor and the invented frugal "
            "diagnostic-technologies, enabling the establishment of their self-esteem and sustainable "
            "livelihood in the process."
        )
        w1 = _file("women-empowerment01.jpg")
        if w1:
            _save_file(home.women_image_1, "women-empowerment01.jpg", w1)
        w2 = _file("women-empowerment02.jpg")
        if w2:
            _save_file(home.women_image_2, "women-empowerment02.jpg", w2)
        home.women_text_2 = (
            "Empowered by a 'primary-care software', this has led to all-in-one real-time data-driven "
            "clinical decision support system allowing for screening and risk-assessment of patients vetted by "
            "remote doctors to ensure high-quality evidence-based tailor-made advice. These centres make "
            "genuine medicines available to the rural population (where spurious medicines are sold in an "
            "unchecked manner), deliver basic physiotherapy services, undertake school & community-based "
            "health education and awareness activities; including manufacturing of simple health products "
            "such as Sanitizer, Face mask, Oral Rehydration Salts, Sanitary Napkins etc."
        )

        home.location_address = "Second Floor, Diamond Jubilee Building, IIT Kharagpur"
        home.location_description = (
            "Available pilot plant and laboratories at CRTDH facility for research, MSME training and "
            "prototype development"
        )

        home.facility_card_1_title = "CRTDH Conference Room & Office"
        f1 = _file("facility/01.jpg")
        if f1:
            _save_file(home.facility_card_1_image, "facility-01.jpg", f1)
        home.facility_card_2_title = "Pilot Plant and Manufacturing Units"
        f2 = _file("facility/02.jpg")
        if f2:
            _save_file(home.facility_card_2_image, "facility-02.jpg", f2)
        home.facility_card_2_link = "/facilities#manufacturing-plants"
        home.facility_card_3_title = "CRTDH Sterile Room"
        f3 = _file("facility/03.jpg")
        if f3:
            _save_file(home.facility_card_3_image, "facility-03.jpg", f3)

        home.chintan_shivir_youtube_id = "PumM2298Zaw"
        home.viksit_bharat_youtube_id = "62PfmqDvzG4"
        office = _file("office.png")
        if office:
            _save_file(home.office_image, "office.png", office)

        home.membership_heading = "Annual Membership for MSME / Startup"
        pdf = _file("Membership-CDH.pdf")
        if pdf:
            _save_file(home.membership_pdf, "Membership-CDH.pdf", pdf)

        home.save()
        self.stdout.write("Home page content set.")
