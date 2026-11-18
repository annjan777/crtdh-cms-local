import html
import re

from rest_framework import serializers

from .models import ContactMessage

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean(value):
    """Drop control characters and HTML-escape: stored text is safe to render anywhere."""
    return html.escape(CONTROL_CHARS.sub("", value).strip(), quote=True)


class ContactMessageCreateSerializer(serializers.Serializer):
    """Public POST /api/v1/contact/. `website` is a honeypot; `turnstile_token` is checked in the view."""

    name = serializers.CharField(max_length=120, min_length=2)
    email = serializers.EmailField(max_length=254)
    phone = serializers.RegexField(r"^[0-9+()\-\s]{6,25}$", required=False, allow_blank=True)
    message = serializers.CharField(max_length=4000, min_length=10)
    website = serializers.CharField(required=False, allow_blank=True, max_length=200)
    turnstile_token = serializers.CharField(required=False, allow_blank=True, max_length=2048)

    def validate(self, attrs):
        for key in ("name", "message", "phone"):
            if attrs.get(key):
                attrs[key] = clean(attrs[key])
        attrs["email"] = attrs["email"].strip().lower()
        return attrs

    def create(self, data):
        return ContactMessage.objects.create(
            name=data["name"], email=data["email"], phone=data.get("phone", ""), message=data["message"]
        )


class ContactMessageSerializer(serializers.ModelSerializer):
    """Used by the staff-only /api/v1/contact-messages/ read endpoint. Fields are HTML-escaped at rest."""

    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "phone", "message", "created_at"]
