from django.db import models
from apps.common.versioning import VersionedModel


class Enterprise(VersionedModel):
    name = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to="enterprises/", blank=True, null=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name
