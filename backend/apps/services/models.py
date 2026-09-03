from django.db import models


class Service(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="services/", blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title
