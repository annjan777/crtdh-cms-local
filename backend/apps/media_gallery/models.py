from django.db import models


class MediaEvent(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class MediaEventImage(models.Model):
    event = models.ForeignKey(MediaEvent, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="media_event_images/")
    caption = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.caption or f"MediaEventImage {self.pk}"


class MediaCoverageLink(models.Model):
    title = models.CharField(max_length=255)
    url = models.URLField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class GalleryImage(models.Model):
    image = models.ImageField(upload_to="gallery_images/")
    caption = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.caption or f"GalleryImage {self.pk}"
