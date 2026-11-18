from rest_framework import serializers

from .models import TeamCategory, TeamMember


class TeamCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamCategory
        fields = ["id", "name", "order", "is_published", "version"]


class TeamMemberSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = TeamMember
        fields = ["id", "category", "category_name", "name", "photo", "designation", "institution", "description", "is_published", "order", "version"]
