from django.db import models

from apps.common.versioning import VersionedModel
from apps.carousel.models import validate_image_position
from apps.publishing.pages import PAGE_CHOICES


class ImageGridBlock(VersionedModel):
    """A named, ordered group of images used on several pages (facilities-manufacturing,
    services images, enterprises demo grid, social-impact/covid-19 grids, home grids, ...).
    `page` is a registry page id (apps/publishing/pages.py), e.g. "facilities", "social-impact".
    """

    page = models.CharField(max_length=100, choices=PAGE_CHOICES)
    section_title = models.CharField(max_length=255, blank=True)
    anchor_slug = models.SlugField(max_length=100, blank=True)
    intro = models.TextField(blank=True, help_text="Optional lead paragraph shown above the grid.")
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["page", "id"]

    def __str__(self):
        return f"{self.page}: {self.section_title or self.anchor_slug or self.pk}"


class ImageGridItem(VersionedModel):
    block = models.ForeignKey(ImageGridBlock, related_name="items", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="image_grid_items/")
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    caption = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.caption or f"Item {self.pk}"


class VideoBlock(VersionedModel):
    title = models.CharField(max_length=255, blank=True)
    page = models.CharField(max_length=100, choices=PAGE_CHOICES)
    youtube_url = models.URLField(blank=True, null=True)
    video_file = models.FileField(upload_to="video_blocks/", blank=True, null=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title or f"VideoBlock {self.pk}"


class Document(VersionedModel):
    class Category(models.TextChoices):
        NEWSLETTER = "newsletter", "Newsletter"
        MEMBERSHIP = "membership", "Membership"
        OTHER = "other", "Other"

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class PageHero(VersionedModel):
    """The photo and headline at the top of one inner page (one row per page). Empty fields fall back to the
    page's built-in wording and an automatically chosen photo."""

    page = models.CharField(max_length=100, choices=PAGE_CHOICES, unique=True)
    eyebrow = models.CharField(max_length=60, blank=True)
    title = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="page_heroes/", blank=True, null=True)
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    image_position = models.CharField(max_length=20, default="center center", blank=True, validators=[validate_image_position])
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["page"]

    def __str__(self):
        return f"{self.page}: {self.title or 'hero'}"


class ResearchStory(VersionedModel):
    """A research theme (Research page) or a lab-to-field step with its evidence (Research translation page)."""

    class Page(models.TextChoices):
        RESEARCH = "research", "Research"
        TRANSLATION = "research-translation", "Research translation"

    class Stage(models.TextChoices):
        NONE = "", "No stage"
        DISCOVERY = "discovery", "Discovery"
        PROTOTYPE = "prototype", "Prototype"
        VALIDATION = "validation", "Validation"
        TRANSLATION = "translation", "Translation"

    page = models.CharField(max_length=40, choices=Page.choices, default=Page.RESEARCH)
    stage = models.CharField(max_length=20, choices=Stage.choices, blank=True, default="")
    title = models.CharField(max_length=160)
    summary = models.TextField(blank=True)
    body = models.TextField(blank=True)
    image = models.ImageField(upload_to="research/", blank=True, null=True)
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    link_url = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "research stories"

    def save(self, *args, **kwargs):
        from apps.common.sanitize import clean_richtext

        self.body = clean_richtext(self.body)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ImpactFigure(VersionedModel):
    """A number shown on a page (for example people reached). Every figure names where it comes from."""

    page = models.CharField(max_length=100, choices=PAGE_CHOICES)
    value = models.CharField(max_length=24)
    label = models.CharField(max_length=80)
    source = models.CharField(max_length=200, help_text="Where this number comes from (a report, register or date).")
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["page", "order"]

    def __str__(self):
        return f"{self.value} {self.label}"
