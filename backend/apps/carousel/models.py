from django.db import models


class HeroSlide(models.Model):
    image = models.ImageField(upload_to="hero_slides/")
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
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.heading} {self.highlight_heading} (Slide {self.pk})"


class ProjectSlide(models.Model):
    image = models.ImageField(upload_to="project_slides/")
    title = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title or f"ProjectSlide {self.pk}"
