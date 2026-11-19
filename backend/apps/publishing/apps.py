from django.apps import AppConfig


class PublishingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.publishing"
    label = "publishing"

    def ready(self):
        from .admin_readonly import make_admin_readonly

        make_admin_readonly()
        from .sanitize_hooks import connect

        connect()
        try:  # backend-security's upload field: feed it the registry's min_width rules (no-op before the merge)
            from apps.common import fields as upload_fields
        except ImportError:
            return
        from .registry import min_widths

        upload_fields.MIN_WIDTHS.update(min_widths())
