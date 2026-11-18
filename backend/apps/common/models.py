from django.db import models
from apps.common.versioning import VersionedModel
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
