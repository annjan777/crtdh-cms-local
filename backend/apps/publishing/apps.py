from django.apps import AppConfig


class PublishingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.publishing"
    label = "publishing"

    def ready(self):
        from .admin_readonly import make_admin_readonly

        make_admin_readonly()
