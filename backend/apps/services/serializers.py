from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "title", "audience", "description", "includes", "how_to_access", "cta_label", "cta_link", "image", "image_alt", "order", "is_published", "version"]
