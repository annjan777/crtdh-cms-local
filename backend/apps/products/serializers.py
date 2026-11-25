from rest_framework import serializers

from .models import Product, ProductImage, ProductPartner


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "product", "image", "image_alt", "order", "is_published", "version"]


class ProductPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPartner
        fields = ["id", "product", "name", "logo", "logo_alt", "is_published", "version"]


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    partners = ProductPartnerSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "status", "summary", "use_case", "order", "images", "partners", "is_published", "version"]
