from django.db import models
from apps.common.versioning import VersionedModel


class Equipment(VersionedModel):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="equipment/", blank=True, null=True)
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "Equipment"

    def __str__(self):
        return self.name
