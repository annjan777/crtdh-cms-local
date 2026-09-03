from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="product_images/")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"ProductImage {self.pk}"


class ProductPartner(models.Model):
    product = models.ForeignKey(Product, related_name="partners", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="product_partners/", blank=True, null=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name
