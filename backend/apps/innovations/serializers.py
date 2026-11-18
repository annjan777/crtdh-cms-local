from rest_framework import serializers

from .models import Innovation, InnovationImage


class InnovationImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InnovationImage
        fields = ["id", "innovation", "image", "image_alt", "caption", "order", "is_published", "version"]


class InnovationSerializer(serializers.ModelSerializer):
    images = InnovationImageSerializer(many=True, read_only=True)

    class Meta:
        model = Innovation
        fields = ["id", "title", "body", "video_url", "order", "images", "is_published", "version"]
