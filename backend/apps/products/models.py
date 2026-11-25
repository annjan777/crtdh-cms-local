from django.db import models
from apps.common.versioning import VersionedModel


class Product(VersionedModel):
    STATUSES = [
        ("", "Not set"),
        ("market", "On the market"),
        ("licensed", "Licensed to an enterprise"),
        ("field", "In field use"),
        ("archived", "No longer offered"),
    ]

    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUSES, blank=True, default="",
                              help_text="Shown as a tag. Set only when confirmed.")
    summary = models.TextField(blank=True, help_text="One or two sentences: what the product does.")
    use_case = models.CharField(max_length=200, blank=True, help_text="Who uses it and where, for example 'Anaemia screening in rural clinics'.")
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
