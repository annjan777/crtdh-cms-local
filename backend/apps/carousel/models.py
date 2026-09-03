from django.db import models


class HeroSlide(models.Model):
    image = models.ImageField(upload_to="hero_slides/")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"HeroSlide {self.pk}"


class ProjectSlide(models.Model):
    image = models.ImageField(upload_to="project_slides/")
    title = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title or f"ProjectSlide {self.pk}"
