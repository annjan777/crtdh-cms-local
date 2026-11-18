from rest_framework import serializers

from .models import GalleryImage, MediaCoverageLink, MediaEvent, MediaEventImage


class MediaEventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaEventImage
        fields = ["id", "event", "image", "image_alt", "caption", "order", "is_published", "version"]


class MediaEventSerializer(serializers.ModelSerializer):
    images = MediaEventImageSerializer(many=True, read_only=True)

    class Meta:
        model = MediaEvent
        fields = ["id", "title", "slug", "description", "event_date", "category", "order", "images", "is_published", "version"]


class MediaCoverageLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaCoverageLink
        fields = ["id", "title", "url", "order", "is_published", "version"]


class GalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryImage
        fields = ["id", "image", "image_alt", "caption", "order", "is_published", "version"]
