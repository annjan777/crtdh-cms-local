from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    label = "common"

    def ready(self):
        from django.db import models
        from rest_framework.serializers import ModelSerializer

        from .fields import SafeFileField, SafeImageField

        ModelSerializer.serializer_field_mapping[models.ImageField] = SafeImageField
        ModelSerializer.serializer_field_mapping[models.FileField] = SafeFileField
