import bleach
from django.db import models

ALLOWED_TAGS = [
    "p", "br", "b", "strong", "i", "em", "u", "a", "ul", "ol", "li",
    "h1", "h2", "h3", "h4", "blockquote", "span", "div", "img",
]
ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "span": ["class"],
    "div": ["class"],
    "*": ["style"],
}


class Innovation(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        if self.body:
            self.body = bleach.clean(
                self.body,
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRS,
                strip=True,
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class InnovationImage(models.Model):
    innovation = models.ForeignKey(Innovation, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="innovation_images/")
    caption = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.caption or f"InnovationImage {self.pk}"
