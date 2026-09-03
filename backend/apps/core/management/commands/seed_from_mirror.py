"""
Seed the CMS database from the scraped static-site HTML mirror.

USAGE
    python manage.py seed_from_mirror [--mirror-path /path/to/crtdh_mirror/site]

WHAT IT DOES
    Parses the HTML files in the mirror (default: /home/claude/crtdh_mirror/site,
    override with --mirror-path) for the well-structured, repeating sections of
    the old static site — hero/project carousels, team, facilities equipment +
    manufacturing grid, services, enterprises + demonstration grid, media
    galleries/coverage links/top gallery, nav, site settings/footer, and the
    newsletter/membership PDFs — and creates the corresponding rows, copying
    each referenced image/PDF from the mirror into the matching model's
    ImageField/FileField (via Django's File wrapper, so `upload_to` is honoured
    and the files land under MEDIA_ROOT correctly).

    The 12 Innovations and 5 Products pages are hand-authored, non-uniform
    layouts that don't parse reliably as a generic loop, so their content
    (title/body/images, taken from actually reading innovations.html and
    product.html) lives in the JSON fixtures under this command's
    `_seed_data/` directory and is loaded verbatim.

IDEMPOTENCY
    This command is idempotent by way of CLEAR + RESEED: at the start of each
    section it deletes all existing rows of the model(s) that section owns,
    then recreates them from the mirror. This is simpler and more predictable
    than get_or_create-with-natural-keys for content that has no natural
    unique key (e.g. two equipment items could plausibly share a name), and
    it means re-running the command after a mirror update just works instead
    of accumulating duplicates. SiteSettings is the one exception: it's a
    true singleton (pk=1) and is updated in place, never deleted.

    Re-running this command is therefore always safe, but it is meant to be
    run ONCE against a fresh/dev database when bootstrapping content — it is
    not an incremental sync tool, and any manual edits made in the admin SPA
    to the models it owns will be wiped on a re-run.

WHAT IT SKIPS
    A handful of images referenced by the old site are not real, fetchable
    assets (an external http://via.placeholder.com URL, one malformed src
    attribute, and a couple of filenames the HTML references that were never
    actually present in the scraped mirror). Those rows are still created
    (with a blank image) rather than dropped outright, and every skip is
    collected and printed in the end-of-run summary rather than raising.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.carousel.models import HeroSlide, ProjectSlide
from apps.common.models import Document, ImageGridBlock, ImageGridItem
from apps.core.models import NavItem, SiteSettings
from apps.enterprises.models import Enterprise
from apps.facilities.models import Equipment
from apps.innovations.models import Innovation, InnovationImage
from apps.media_gallery.models import GalleryImage, MediaCoverageLink, MediaEvent, MediaEventImage
from apps.products.models import Product, ProductImage, ProductPartner
from apps.services.models import Service
from apps.team.models import TeamCategory, TeamMember

DEFAULT_MIRROR_PATH = "/home/claude/crtdh_mirror/site"

SEED_DATA_DIR = Path(__file__).resolve().parent / "_seed_data"

DOCUMENTS = [
    {
        "title": "Quarterly Newsletter 1",
        "path": "images/Quarterly-news-letter-1.pdf",
        "category": Document.Category.NEWSLETTER,
    },
    {
        "title": "Quarterly Newsletter 2",
        "path": "images/Quarterly-news-letter-2.pdf",
        "category": Document.Category.NEWSLETTER,
    },
    {
        "title": "Membership Details (CRTDH)",
        "path": "images/Membership-CDH.pdf",
        "category": Document.Category.MEMBERSHIP,
    },
    {
        "title": "Write-up: Activities around CRTDH",
        "path": "images/write-up-activities-around-CRTDH.docx.pdf",
        "category": Document.Category.OTHER,
    },
]

TEAM_CATEGORIES_IN_ORDER = [
    "Principal Investigator",
    "Co-Principal Investigator",
    "Other Members",
    "Project Manager",
    "Project Staff",
    "Medical Staff",
]

MEDIA_NAMED_SECTIONS = [
    # (anchor id in the HTML, slug for MediaEvent)
    ("pathologyandeyeclinic", "pathologyandeyeclinic"),
    ("ruralhealthcarefoundation", "ruralhealthcarefoundation"),
    ("anemiacampkuchlachati", "anemiacampkuchlachati"),
    ("arjunmalhotra", "arjunmalhotra"),
    ("conclave", "conclave"),
    ("chintanshivir", "chintanshivir"),
    ("jio", "jio"),
]


class Command(BaseCommand):
    help = "Seed the CMS database from the scraped static-site HTML mirror. See module docstring for details."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mirror-path",
            default=DEFAULT_MIRROR_PATH,
            help=f"Path to the mirror's site/ directory (default: {DEFAULT_MIRROR_PATH})",
        )

    def handle(self, *args, **options):
        self.mirror_root = Path(options["mirror_path"]).resolve()
        if not self.mirror_root.is_dir():
            raise CommandError(f"Mirror path does not exist or is not a directory: {self.mirror_root}")

        self.stats = {}
        self.skipped = []

        with transaction.atomic():
            index_soup = self._soup("index.html")
            self._seed_site_settings_and_nav(index_soup)
            self._seed_hero_slides(index_soup)

            innovations_soup = self._soup("innovations.html")
            self._seed_project_slides(innovations_soup)

            self._seed_team(self._soup("team.html"))

            facilities_soup = self._soup("facilities.html")
            self._seed_equipment(facilities_soup)
            self._seed_manufacturing_grid(facilities_soup)

            self._seed_services(self._soup("services.html"))

            enterprises_soup = self._soup("enterprises.html")
            self._seed_enterprises(enterprises_soup)
            self._seed_enterprises_demo_grid(enterprises_soup)

            self._seed_media(self._soup("media.html"))
            self._seed_documents()
            self._seed_innovations()
            self._seed_products()

        self._print_summary()

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    def _soup(self, filename):
        path = self.mirror_root / filename
        html = path.read_text(encoding="utf-8", errors="replace")
        return BeautifulSoup(html, "lxml")

    def _bump(self, model_name, n=1):
        self.stats[model_name] = self.stats.get(model_name, 0) + n

    def _skip(self, what, reason):
        self.skipped.append(f"{what}: {reason}")

    def _resolve_asset(self, relpath):
        """Resolve a mirror-relative asset path (as it appears in a scraped `src`/`href`
        attribute, e.g. "images/foo/bar.jpg") to an absolute Path, or None (with a
        logged skip) if it isn't a real local file — e.g. an external placeholder
        URL, a malformed src, or a filename the HTML references but the mirror never
        actually captured."""
        if not relpath:
            return None
        if relpath.startswith("http://") or relpath.startswith("https://"):
            self._skip(relpath, "external URL, not a local asset — skipped")
            return None
        relpath = relpath.lstrip("./")
        abs_path = (self.mirror_root / relpath).resolve()
        try:
            abs_path.relative_to(self.mirror_root)
        except ValueError:
            self._skip(relpath, "malformed src (does not resolve under mirror root) — skipped")
            return None
        if "/" not in relpath and not relpath.startswith("images"):
            # Things like the bare literal "210room" — not a path at all.
            self._skip(relpath, "malformed src (not a file path) — skipped")
            return None
        if not abs_path.is_file():
            self._skip(relpath, "referenced in HTML but missing from mirror — skipped")
            return None
        return abs_path

    def _attach_file(self, field, relpath, filename_prefix=""):
        """Attach the mirror asset at `relpath` to a Django File/ImageField. Returns
        True if attached, False if skipped (already logged by _resolve_asset)."""
        abs_path = self._resolve_asset(relpath)
        if abs_path is None:
            return False
        with abs_path.open("rb") as fh:
            field.save(filename_prefix + abs_path.name, File(fh), save=False)
        return True

    # ------------------------------------------------------------------ #
    # site settings / nav / hero
    # ------------------------------------------------------------------ #

    def _seed_site_settings_and_nav(self, soup):
        settings_obj = SiteSettings.load()
        settings_obj.address = (
            "Second Floor (204), Bioscience Building, Diamond Jubilee Complex, "
            "IIT Kharagpur, West Midnapur- 721302"
        )
        settings_obj.phone_primary = "+91-88200 51894"
        settings_obj.phone_secondary = ""
        settings_obj.email_primary = "suman@mech.iitkgp.ac.in"
        settings_obj.email_secondary = "sohom.banner@gmail.com"
        settings_obj.map_embed_url = ""
        # Social links are all href="#" placeholders in the mirror — leave blank
        # rather than importing "#".
        settings_obj.facebook_url = ""
        settings_obj.linkedin_url = ""
        settings_obj.instagram_url = ""
        settings_obj.twitter_url = ""
        settings_obj.save()
        self._bump("SiteSettings")

        NavItem.objects.all().delete()
        nav_ul = soup.find("ul", class_="navbar-nav")
        for order, a in enumerate(nav_ul.find_all("a")):
            label = a.get_text(strip=True)
            if not label:
                continue
            NavItem.objects.create(label=label, url=self._route_for(a.get("href", "")), order=order)
            self._bump("NavItem")

    # The mirror's nav <a href> values are the old static site's raw
    # filenames (e.g. "about.html", "contact-us.html") — not the new React
    # Router paths the public frontend actually serves ("/about",
    # "/contact"). Map the ones we know about; anything unrecognised falls
    # back to a best-effort slugification so it's at least close.
    _LEGACY_HREF_TO_ROUTE = {
        "index.html": "/",
        "about.html": "/about",
        "team.html": "/team",
        "innovations.html": "/innovations",
        "facilities.html": "/facilities",
        "services.html": "/services",
        "enterprises.html": "/enterprises",
        "product.html": "/product",
        "social-impact.html": "/social-impact",
        "covid-19.html": "/covid-19",
        "media.html": "/media",
        "contact-us.html": "/contact",
    }

    def _route_for(self, href):
        href = (href or "").strip()
        if not href or href == "#":
            return "/"
        if href.startswith("http") or href.startswith("/"):
            return href
        if href in self._LEGACY_HREF_TO_ROUTE:
            return self._LEGACY_HREF_TO_ROUTE[href]
        # Best-effort fallback: "foo.html" -> "/foo", "foo-us.html" -> "/foo-us"
        return "/" + re.sub(r"\.html?$", "", href)

    def _seed_hero_slides(self, soup):
        HeroSlide.objects.all().delete()
        hero = soup.find(id="hero-image")
        if hero is None:
            self._skip("hero-image", "#hero-image not found in index.html")
            return
        for order, img in enumerate(hero.find_all("img")):
            slide = HeroSlide(order=order)
            if self._attach_file(slide.image, img.get("src")):
                slide.save()
                self._bump("HeroSlide")
            else:
                self._skip(f"HeroSlide #{order}", "image missing, slide not created")

    # ------------------------------------------------------------------ #
    # innovations page: project carousel
    # ------------------------------------------------------------------ #

    def _seed_project_slides(self, soup):
        ProjectSlide.objects.all().delete()
        carousel = soup.find(id="project-slide")
        if carousel is None:
            self._skip("project-slide", "#project-slide not found in innovations.html")
            return
        items = carousel.find_all("div", class_="item")
        for order, item in enumerate(items):
            img = item.find("img")
            title_el = item.find("h3")
            title = title_el.get_text(strip=True) if title_el else ""
            slide = ProjectSlide(title=title, order=order)
            if self._attach_file(slide.image, img.get("src") if img else None):
                slide.save()
                self._bump("ProjectSlide")
            else:
                self._skip(f"ProjectSlide {title!r}", "image missing, slide not created")

    # ------------------------------------------------------------------ #
    # team
    # ------------------------------------------------------------------ #

    def _seed_team(self, soup):
        TeamMember.objects.all().delete()
        TeamCategory.objects.all().delete()

        categories = {}
        for order, name in enumerate(TEAM_CATEGORIES_IN_ORDER):
            categories[name] = TeamCategory.objects.create(name=name, order=order)
            self._bump("TeamCategory")

        current_cat_name = None
        member_order = {name: 0 for name in TEAM_CATEGORIES_IN_ORDER}
        for el in soup.find_all(["h3", "h4", "div"]):
            if el.name in ("h3", "h4"):
                txt = el.get_text(strip=True).rstrip(":")
                if txt in categories:
                    current_cat_name = txt
            elif el.name == "div" and "card" in (el.get("class") or []):
                if current_cat_name is None:
                    continue
                img = el.find("img")
                name_el = el.find(["h5", "h4", "p"])
                name = name_el.get_text(strip=True) if name_el else ""
                if not name:
                    continue
                member = TeamMember(
                    category=categories[current_cat_name],
                    name=name,
                    order=member_order[current_cat_name],
                )
                member_order[current_cat_name] += 1
                self._attach_file(member.photo, img.get("src") if img else None)
                member.save()
                self._bump("TeamMember")

    # ------------------------------------------------------------------ #
    # facilities
    # ------------------------------------------------------------------ #

    def _seed_equipment(self, soup):
        Equipment.objects.all().delete()
        toggles = soup.find_all("div", attrs={"data-bs-toggle": "collapse"})
        for order, toggle in enumerate(toggles):
            target_id = toggle.get("data-bs-target", "").lstrip("#")
            name = " ".join(toggle.get_text(strip=True).split())
            collapse = soup.find(id=target_id)
            img = collapse.find("img") if collapse else None
            src = img.get("src") if img else None
            equip = Equipment(name=name, order=order)
            self._attach_file(equip.image, src)  # OK if this fails; image is nullable
            equip.save()
            self._bump("Equipment")

    def _seed_manufacturing_grid(self, soup):
        ImageGridBlock.objects.filter(page="facilities", anchor_slug="manufacturingplants").delete()
        anchor = soup.find(id="manufacturingplants")
        if anchor is None:
            self._skip("manufacturingplants", "#manufacturingplants not found in facilities.html")
            return
        block = ImageGridBlock.objects.create(
            page="facilities",
            section_title="Manufacturing plants and demonstration units",
            anchor_slug="manufacturingplants",
        )
        self._bump("ImageGridBlock")
        row = anchor.find_next_sibling("div", class_="row")
        imgs = row.find_all("img") if row else []
        for order, img in enumerate(imgs):
            item = ImageGridItem(block=block, order=order)
            if self._attach_file(item.image, img.get("src")):
                item.save()
                self._bump("ImageGridItem")
            else:
                self._skip(f"manufacturingplants item #{order}", "image missing, item not created")

    # ------------------------------------------------------------------ #
    # services
    # ------------------------------------------------------------------ #

    def _seed_services(self, soup):
        Service.objects.all().delete()
        cards = soup.find_all(class_="facility-card")
        for order, card in enumerate(cards):
            img = card.find("img")
            text_box = card.find(class_="facility-text")
            title = ""
            if text_box:
                h2 = text_box.find("h2")
                if h2:
                    title = " ".join(h2.get_text(separator=" ", strip=True).split())
            service = Service(title=title, order=order)
            self._attach_file(service.image, img.get("src") if img else None)
            service.save()
            self._bump("Service")

    # ------------------------------------------------------------------ #
    # enterprises
    # ------------------------------------------------------------------ #

    def _seed_enterprises(self, soup):
        Enterprise.objects.all().delete()
        boxes = soup.find_all(class_="msmes-list-box")
        for order, box in enumerate(boxes):
            img = box.find("img")
            title_el = box.find("h5", class_="card-title") or box.find(["h3", "h4", "h5"])
            subtitle_el = box.find("p", class_="card-text") or box.find("p")
            name = title_el.get_text(strip=True) if title_el else ""
            subtitle = subtitle_el.get_text(strip=True) if subtitle_el else ""
            if not name:
                continue
            ent = Enterprise(name=name, subtitle=subtitle, order=order)
            if img:
                self._attach_file(ent.logo, img.get("src"))
            ent.save()
            self._bump("Enterprise")

    def _seed_enterprises_demo_grid(self, soup):
        ImageGridBlock.objects.filter(page="enterprises", anchor_slug="demonstration").delete()
        imgs = soup.find_all("img", src=lambda s: s and "images/demonstration/" in s)
        if not imgs:
            self._skip("enterprises demonstration grid", "no images/demonstration/* <img> found")
            return
        block = ImageGridBlock.objects.create(
            page="enterprises",
            section_title="Demonstration And Training Of MSMEs",
            anchor_slug="demonstration",
        )
        self._bump("ImageGridBlock")
        for order, img in enumerate(imgs):
            item = ImageGridItem(block=block, order=order)
            if self._attach_file(item.image, img.get("src")):
                item.save()
                self._bump("ImageGridItem")
            else:
                self._skip(f"demonstration item #{order}", "image missing, item not created")

    # ------------------------------------------------------------------ #
    # media / gallery
    # ------------------------------------------------------------------ #

    def _seed_media(self, soup):
        GalleryImage.objects.all().delete()
        MediaCoverageLink.objects.all().delete()
        MediaEvent.objects.all().delete()  # cascades to MediaEventImage

        # --- top gallery (6 captioned images) ---
        # NB: the mirror's top-gallery <section> has an unclosed <div class="container">
        # (a genuine bug in the scraped HTML), which makes lxml fold later sections into
        # it when you walk by *section* boundaries — find_parent("section") ends up
        # grabbing way more than the 6 intended images. The heading row's own <div
        # class="row"> sibling is well-formed, so anchor on that instead.
        gallery_h2 = soup.find(lambda tag: tag.name == "h2" and "Gallery" == tag.get_text(strip=True))
        if gallery_h2 is None:
            self._skip("media top gallery", "could not find the 'Gallery' <h2>")
        else:
            heading_row = gallery_h2.find_parent("div", class_="row")
            images_row = heading_row.find_next_sibling("div", class_="row") if heading_row else None
            boxes = images_row.find_all(class_="paper-based-box") if images_row else []
            for order, box in enumerate(boxes):
                img = box.find("img")
                cap_el = box.find(class_="paper-based-box-text")
                caption = cap_el.get_text(strip=True) if cap_el else ""
                gi = GalleryImage(caption=caption, order=order)
                if self._attach_file(gi.image, img.get("src") if img else None):
                    gi.save()
                    self._bump("GalleryImage")
                else:
                    self._skip(f"GalleryImage {caption!r}", "image missing, item not created")

        # --- media coverage links ---
        coverage_box = soup.find(class_="interactions-text-box")
        if coverage_box is None:
            self._skip("media coverage links", "could not find .interactions-text-box")
        else:
            for order, a in enumerate(coverage_box.find_all("a", class_="link")):
                url = a.get("href", "").strip()
                title = a.get_text(strip=True)
                if not url:
                    continue
                MediaCoverageLink.objects.create(title=title, url=url, order=order)
                self._bump("MediaCoverageLink")

        # --- named sub-galleries with a real HTML anchor id ---
        for event_order, (anchor_id, slug) in enumerate(MEDIA_NAMED_SECTIONS):
            section = soup.find(id=anchor_id)
            if section is None:
                self._skip(f"MediaEvent {slug}", f"#{anchor_id} not found in media.html")
                continue
            h3 = section.find("h3")
            title = h3.get_text(strip=True) if h3 else slug
            event = MediaEvent.objects.create(title=title, slug=slug, order=event_order)
            self._bump("MediaEvent")
            for order, img in enumerate(section.find_all("img")):
                mei = MediaEventImage(event=event, order=order)
                if self._attach_file(mei.image, img.get("src")):
                    mei.save()
                    self._bump("MediaEventImage")
                else:
                    self._skip(f"{slug} image #{order}", "image missing, item not created")

        # --- "Other Ongoing Activities" — no real anchor id in the source ---
        other_h3 = soup.find(lambda tag: tag.name == "h3" and tag.get_text(strip=True) == "Other Ongoing Activities")
        if other_h3 is None:
            self._skip("MediaEvent other-ongoing-activities", "'Other Ongoing Activities' heading not found")
        else:
            section = other_h3.find_parent("section")
            event = MediaEvent.objects.create(
                title="Other Ongoing Activities",
                slug="other-ongoing-activities",
                order=len(MEDIA_NAMED_SECTIONS),
            )
            self._bump("MediaEvent")
            for order, img in enumerate(section.find_all("img")):
                mei = MediaEventImage(event=event, order=order)
                if self._attach_file(mei.image, img.get("src")):
                    mei.save()
                    self._bump("MediaEventImage")
                else:
                    self._skip(f"other-ongoing-activities image #{order}", "image missing, item not created")

    # ------------------------------------------------------------------ #
    # documents (PDFs)
    # ------------------------------------------------------------------ #

    def _seed_documents(self):
        Document.objects.all().delete()
        for order, doc in enumerate(DOCUMENTS):
            abs_path = self._resolve_asset(doc["path"])
            if abs_path is None:
                self._skip(f"Document {doc['title']!r}", "PDF missing, document not created")
                continue
            d = Document(title=doc["title"], category=doc["category"], order=order)
            with abs_path.open("rb") as fh:
                d.file.save(abs_path.name, File(fh), save=False)
            d.save()
            self._bump("Document")

    # ------------------------------------------------------------------ #
    # innovations / products (hand-authored JSON fixtures)
    # ------------------------------------------------------------------ #

    def _seed_innovations(self):
        Innovation.objects.all().delete()  # cascades to InnovationImage
        data = json.loads((SEED_DATA_DIR / "innovations.json").read_text(encoding="utf-8"))
        for order, entry in enumerate(data):
            inv = Innovation(
                title=entry["title"],
                body=entry.get("body", ""),
                video_url=entry.get("video_url") or None,
                order=order,
            )
            inv.save()
            self._bump("Innovation")
            for img_order, img_entry in enumerate(entry.get("images", [])):
                ii = InnovationImage(
                    innovation=inv,
                    caption=img_entry.get("caption", ""),
                    order=img_order,
                )
                if self._attach_file(ii.image, img_entry["path"]):
                    ii.save()
                    self._bump("InnovationImage")
                else:
                    self._skip(f"InnovationImage for {inv.title!r}", "image missing, item not created")

    def _seed_products(self):
        Product.objects.all().delete()  # cascades to ProductImage / ProductPartner
        data = json.loads((SEED_DATA_DIR / "products.json").read_text(encoding="utf-8"))
        for order, entry in enumerate(data):
            product = Product(name=entry["name"], order=order)
            product.save()
            self._bump("Product")
            for img_order, img_path in enumerate(entry.get("images", [])):
                pi = ProductImage(product=product, order=img_order)
                if self._attach_file(pi.image, img_path):
                    pi.save()
                    self._bump("ProductImage")
                else:
                    self._skip(f"ProductImage for {product.name!r}", "image missing, item not created")
            for partner_entry in entry.get("partners", []):
                pp = ProductPartner(product=product, name=partner_entry["name"])
                logo_path = partner_entry.get("logo")
                if logo_path:
                    self._attach_file(pp.logo, logo_path)
                pp.save()
                self._bump("ProductPartner")

    # ------------------------------------------------------------------ #
    # summary
    # ------------------------------------------------------------------ #

    def _print_summary(self):
        self.stdout.write(self.style.SUCCESS("\n=== seed_from_mirror: done ==="))
        self.stdout.write("Rows created per model:")
        for model_name in sorted(self.stats):
            self.stdout.write(f"  {model_name}: {self.stats[model_name]}")
        self.stdout.write(f"\nSkipped ({len(self.skipped)}):")
        if not self.skipped:
            self.stdout.write("  (none)")
        for line in self.skipped:
            self.stdout.write(f"  - {line}")
