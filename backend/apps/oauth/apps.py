from django.apps import AppConfig


class OAuthConfig(AppConfig):
    name = "apps.oauth"
    label = "cms_oauth"
    verbose_name = "Claude connector (OAuth)"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import signals  # noqa: F401  (connects revocation receivers)
