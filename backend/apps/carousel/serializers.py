from rest_framework import serializers

from .models import HeroSlide, ProjectSlide


class HeroSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroSlide
        fields = "__all__"


class ProjectSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSlide
        fields = ["id", "image", "image_alt", "title", "order", "is_published", "version"]
