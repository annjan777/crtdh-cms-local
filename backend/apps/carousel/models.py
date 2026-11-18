from django.db import models
from apps.common.versioning import VersionedModel


class HeroSlide(VersionedModel):
    image = models.ImageField(upload_to="hero_slides/")
    alt_text = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    eyebrow = models.CharField(max_length=255, blank=True, default="DSIR · GOVERNMENT OF INDIA")
    heading = models.CharField(max_length=255, blank=True, default="Common Research &")
    highlight_heading = models.CharField(max_length=255, blank=True, default="Technology Development")
    heading_end = models.CharField(max_length=255, blank=True, default="Hub")
    description = models.TextField(blank=True, default="Building affordable healthcare technology for a billion people, at IIT Kharagpur.")
    primary_button_label = models.CharField(max_length=100, blank=True, default="Explore Innovations")
    primary_button_link = models.CharField(max_length=255, blank=True, default="/innovations")
    secondary_button_label = models.CharField(max_length=100, blank=True, default="About CRTDH")
    secondary_button_link = models.CharField(max_length=255, blank=True, default="/about")
    is_published = models.BooleanField(default=True)
    # Which part of the photo stays in view when the hero crops it (CSS object-position).
    IMAGE_POSITION_CHOICES = [
        ("center center", "Centre"),
        ("left center", "Left"),
        ("right center", "Right"),
        ("center top", "Top"),
        ("center bottom", "Bottom"),
    ]
    image_position = models.CharField(
        max_length=20, choices=IMAGE_POSITION_CHOICES, default="center center", blank=True
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.heading} {self.highlight_heading} (Slide {self.pk})"


class ProjectSlide(VersionedModel):
    image = models.ImageField(upload_to="project_slides/")
    title = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title or f"ProjectSlide {self.pk}"
