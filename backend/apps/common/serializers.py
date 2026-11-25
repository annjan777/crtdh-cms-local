from rest_framework import serializers

from .models import Document, ImageGridBlock, ImageGridItem, ImpactFigure, PageHero, ResearchStory, VideoBlock


class ImageGridItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageGridItem
        fields = ["id", "block", "image", "image_alt", "caption", "order", "is_published", "version"]


class ImageGridBlockSerializer(serializers.ModelSerializer):
    items = ImageGridItemSerializer(many=True, read_only=True)

    class Meta:
        model = ImageGridBlock
        fields = ["id", "page", "section_title", "anchor_slug", "intro", "items", "is_published", "version"]


class VideoBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoBlock
        fields = ["id", "title", "page", "youtube_url", "video_file", "order", "is_published", "version"]


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "title", "file", "category", "order", "is_published", "version"]


class PageHeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageHero
        fields = ["id", "page", "eyebrow", "title", "description", "image", "image_alt", "image_position", "is_published", "version"]


class ResearchStorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchStory
        fields = ["id", "page", "stage", "title", "summary", "body", "image", "image_alt", "link_url", "order", "is_published", "version"]


class ImpactFigureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpactFigure
        fields = ["id", "page", "value", "label", "source", "order", "is_published", "version"]
