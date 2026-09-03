from django.db import models


class Equipment(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="equipment/", blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "Equipment"

    def __str__(self):
        return self.name
