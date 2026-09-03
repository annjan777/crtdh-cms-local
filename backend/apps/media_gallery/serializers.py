from rest_framework import serializers

from .models import GalleryImage, MediaCoverageLink, MediaEvent, MediaEventImage


class MediaEventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaEventImage
        fields = ["id", "event", "image", "caption", "order"]


class MediaEventSerializer(serializers.ModelSerializer):
    images = MediaEventImageSerializer(many=True, read_only=True)

    class Meta:
        model = MediaEvent
        fields = ["id", "title", "slug", "order", "images"]


class MediaCoverageLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaCoverageLink
        fields = ["id", "title", "url", "order"]


class GalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryImage
        fields = ["id", "image", "caption", "order"]
