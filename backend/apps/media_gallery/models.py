from django.db import models
from apps.common.versioning import VersionedModel


class MediaEvent(VersionedModel):
    CATEGORY_CHOICES = [
        ("events", "Events"),
        ("health-camps", "Health Camps"),
        ("community-outreach", "Community Outreach"),
        ("facilities", "Facilities"),
        ("press", "Press Coverage"),
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="Left empty, it is made from the title.")
    # Optional details shown on the public Media page; all may be left blank.
    description = models.TextField(blank=True, default="")
    event_date = models.DateField(null=True, blank=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, blank=True, default="")
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.title)[:240] or "event"
            slug, n = base, 2
            while MediaEvent.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class MediaEventImage(VersionedModel):
    event = models.ForeignKey(MediaEvent, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="media_event_images/")
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    caption = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.caption or f"MediaEventImage {self.pk}"


class MediaCoverageLink(VersionedModel):
    title = models.CharField(max_length=255)
    url = models.URLField()
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class GalleryImage(VersionedModel):
    image = models.ImageField(upload_to="gallery_images/")
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    caption = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.caption or f"GalleryImage {self.pk}"
