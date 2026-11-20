import re

from django.core.exceptions import ValidationError
from django.db import models
from apps.common.versioning import VersionedModel


_POSITION_WORD = r"(?:left|center|right|top|bottom)"
_POSITION_PCT = r"(?:100|[1-9]?\d)(?:\.\d)?%"
_POSITION_RE = re.compile(rf"^(?:{_POSITION_WORD} {_POSITION_WORD}|{_POSITION_PCT} {_POSITION_PCT})$")


def validate_image_position(value):
    if value and not _POSITION_RE.match(value):
        raise ValidationError('Use a focus point such as "30% 45%" (across, down) or "center center".')


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
    # Which point of the photo stays in view when the hero crops it: a CSS object-position, either a
    # keyword pair ("center center", "right top") or the focus point the editor clicks ("30% 45%").
    image_position = models.CharField(
        max_length=20, default="center center", blank=True, validators=[validate_image_position]
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.heading} {self.highlight_heading} (Slide {self.pk})"


class ProjectSlide(VersionedModel):
    image = models.ImageField(upload_to="project_slides/")
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    title = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title or f"ProjectSlide {self.pk}"
