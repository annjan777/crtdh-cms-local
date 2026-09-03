from rest_framework import serializers

from .models import ContactMessage


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    """Used by the public POST /api/v1/contact/ endpoint."""

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "message"]


class ContactMessageSerializer(serializers.ModelSerializer):
    """Used by the staff-only /api/v1/contact-messages/ read endpoint."""

    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "phone", "message", "created_at"]
