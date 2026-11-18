from rest_framework import serializers

from .models import Document, ImageGridBlock, ImageGridItem, VideoBlock


class ImageGridItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageGridItem
        fields = ["id", "block", "image", "caption", "order", "is_published", "version"]


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
