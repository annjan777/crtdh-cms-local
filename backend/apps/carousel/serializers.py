from rest_framework import serializers

from .models import HeroSlide, ProjectSlide, normalise_image_position


class HeroSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroSlide
        fields = "__all__"

    def validate_image_position(self, value):
        return normalise_image_position(value)


class ProjectSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSlide
        fields = ["id", "image", "image_alt", "title", "order", "is_published", "version"]
