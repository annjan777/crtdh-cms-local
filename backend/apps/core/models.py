from django.db import models
from apps.common.versioning import VersionedModel


class SiteSettings(VersionedModel):
    """Singleton row (pk is always forced to 1). Use SiteSettings.load() to fetch/create it."""

    address = models.TextField(blank=True)
    phone_primary = models.CharField(max_length=50, blank=True)
    phone_secondary = models.CharField(max_length=50, blank=True)
    email_primary = models.EmailField(blank=True)
    email_secondary = models.EmailField(blank=True)
    map_embed_url = models.URLField(blank=True, max_length=500)
    facebook_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    # Header partner marks — IIT Kharagpur crest (left) and DSIR emblem
    # (right), flanking the nav bar on every page of the original site.
    logo_left = models.ImageField(upload_to="brand/", blank=True, null=True)
    logo_left_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    logo_right = models.ImageField(upload_to="brand/", blank=True, null=True)
    logo_right_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    # CRTDH's own mark, shown next to the "CRTDH" wordmark in the header/footer.
    site_logo = models.ImageField(upload_to="brand/", blank=True, null=True)
    site_logo_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Singleton: never actually delete the row.
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Site settings"


class NavItem(VersionedModel):
    label = models.CharField(max_length=100)
    url = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    in_more = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.label


class NewsItem(VersionedModel):
    text = models.CharField(max_length=500)
    link_url = models.CharField(max_length=500, blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text[:60]


class FocusArea(VersionedModel):
    title = models.CharField(max_length=255)
    color = models.CharField(max_length=32, blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class ObjectiveRow(VersionedModel):
    # Groups rows under a shared row-header in the Objectives table (e.g.
    # "Ideation", "Capacity-building", "Key risks mitigation") — several
    # rows share one category, matching the rowspan grouping on the
    # original site.
    category = models.CharField(max_length=120, blank=True)
    task = models.CharField(max_length=500)
    outcome = models.CharField(max_length=500, blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.task[:60]


class TimelineEntry(VersionedModel):
    year = models.CharField(max_length=20)
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="timeline/", blank=True, null=True)
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.year} - {self.title}"


class AboutPage(VersionedModel):
    """Singleton row (pk always 1, same pattern as SiteSettings) holding the
    long-form prose on the About page — the sections that aren't structured
    lists (FocusArea/ObjectiveRow/TimelineEntry already cover those)."""

    intro = models.TextField(blank=True, help_text="'About CRTDH' opening paragraph(s).")
    mission_vision = models.TextField(blank=True)
    focus_intro = models.TextField(blank=True, help_text="Short tagline(s) shown above the Focus Area color blocks, one per line.")
    ecosystem_heading = models.CharField(max_length=255, blank=True)
    ecosystem_image = models.ImageField(upload_to="about/", blank=True, null=True)
    ecosystem_image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    pi_desk_image = models.ImageField(upload_to="about/", blank=True, null=True)
    pi_desk_image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    pi_desk_document = models.FileField(upload_to="about/", blank=True, null=True)
    dsir_about = models.TextField(blank=True)
    iitkgp_about = models.TextField(blank=True)

    class Meta:
        verbose_name = "About page"
        verbose_name_plural = "About page"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "About page"


class HomePage(VersionedModel):
    """Singleton row (pk always 1) holding the homepage's long-form
    sections that sit below the hero/stats/highlights — Objective,
    Enterprises Engagement, Women Empowerment, Location & Facility, and the
    Annual Membership callout — none of which fit the reusable
    ImageGridBlock shape because each has its own fixed layout of
    prose + named images."""

    objective_text = models.TextField(blank=True)

    enterprises_text = models.TextField(blank=True)
    enterprises_image_1 = models.ImageField(upload_to="home/", blank=True, null=True)
    enterprises_image_1_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    enterprises_image_2 = models.ImageField(upload_to="home/", blank=True, null=True)
    enterprises_image_2_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    msme_map_image = models.ImageField(upload_to="home/", blank=True, null=True)
    msme_map_image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    msme_caption = models.CharField(max_length=255, blank=True, default="MSME cluster supported by CRTDH, IIT KGP")

    women_text_1 = models.TextField(blank=True)
    women_image_1 = models.ImageField(upload_to="home/", blank=True, null=True)
    women_image_1_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    women_image_2 = models.ImageField(upload_to="home/", blank=True, null=True)
    women_image_2_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    women_text_2 = models.TextField(blank=True)

    location_address = models.CharField(max_length=255, blank=True, default="Second Floor, Diamond Jubilee Building, IIT Kharagpur")
    location_description = models.TextField(blank=True, default="Available pilot plant and laboratories at CRTDH facility for research, MSME training and prototype development")

    facility_card_1_title = models.CharField(max_length=255, blank=True, default="CRTDH Conference Room & Office")
    facility_card_1_image = models.ImageField(upload_to="home/facility/", blank=True, null=True)
    facility_card_1_image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    facility_card_1_link = models.CharField(max_length=255, blank=True)
    facility_card_2_title = models.CharField(max_length=255, blank=True, default="Pilot Plant and Manufacturing Units")
    facility_card_2_image = models.ImageField(upload_to="home/facility/", blank=True, null=True)
    facility_card_2_image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    facility_card_2_link = models.CharField(max_length=255, blank=True, default="/facilities#manufacturing-plants")
    facility_card_3_title = models.CharField(max_length=255, blank=True, default="CRTDH Sterile Room")
    facility_card_3_image = models.ImageField(upload_to="home/facility/", blank=True, null=True)
    facility_card_3_image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    facility_card_3_link = models.CharField(max_length=255, blank=True)

    chintan_shivir_youtube_id = models.CharField(max_length=32, blank=True)
    viksit_bharat_youtube_id = models.CharField(max_length=32, blank=True)
    office_image = models.ImageField(upload_to="home/", blank=True, null=True)
    office_image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")

    membership_heading = models.CharField(max_length=255, blank=True, default="Annual Membership for MSME / Startup")
    membership_pdf = models.FileField(upload_to="home/", blank=True, null=True)

    # The three pathways under the home hero (title, one line, link, icon).
    PATHWAY_ICONS = [
        ("technology", "Technology (chip)"),
        ("research", "Research (flask)"),
        ("rural", "Communities (people)"),
        ("facilities", "Facilities (microscope)"),
        ("industry", "Industry (handshake)"),
        ("training", "Training (cap)"),
    ]
    pathway_1_title = models.CharField(max_length=60, blank=True, default="Technology")
    pathway_1_text = models.CharField(max_length=140, blank=True, default="Developing indigenous, affordable healthcare solutions for practical use.")
    pathway_1_link = models.CharField(max_length=255, blank=True, default="/innovations")
    pathway_1_icon = models.CharField(max_length=20, choices=PATHWAY_ICONS, default="technology")
    pathway_2_title = models.CharField(max_length=60, blank=True, default="Research translation")
    pathway_2_text = models.CharField(max_length=140, blank=True, default="Moving healthcare innovations from the laboratory towards practical use.")
    pathway_2_link = models.CharField(max_length=255, blank=True, default="/research-translation")
    pathway_2_icon = models.CharField(max_length=20, choices=PATHWAY_ICONS, default="research")
    pathway_3_title = models.CharField(max_length=60, blank=True, default="Rural impact")
    pathway_3_text = models.CharField(max_length=140, blank=True, default="Bringing healthcare innovations closer to underserved communities.")
    pathway_3_link = models.CharField(max_length=255, blank=True, default="/social-impact")
    pathway_3_icon = models.CharField(max_length=20, choices=PATHWAY_ICONS, default="rural")

    # "Our focus": the short mission story under the pathways, with a photo in a curved frame.
    focus_eyebrow = models.CharField(max_length=40, blank=True, default="Our focus")
    focus_heading = models.CharField(max_length=80, blank=True, default="From lab to last mile.")
    focus_text = models.TextField(
        blank=True,
        default="Developing, validating and translating healthcare technologies that are practical, scalable and "
        "relevant to real-world needs.",
    )
    focus_image = models.ImageField(upload_to="home/", blank=True, null=True)
    focus_image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    focus_link_label = models.CharField(max_length=40, blank=True, default="Know more about CRTDH")
    focus_link = models.CharField(max_length=255, blank=True, default="/about")

    class Meta:
        verbose_name = "Home page"
        verbose_name_plural = "Home page"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Home page"
