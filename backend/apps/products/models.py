from django.db import models
from apps.common.versioning import VersionedModel


class Product(VersionedModel):
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class ProductImage(VersionedModel):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="product_images/")
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"ProductImage {self.pk}"


class ProductPartner(VersionedModel):
    product = models.ForeignKey(Product, related_name="partners", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="product_partners/", blank=True, null=True)
    logo_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name
