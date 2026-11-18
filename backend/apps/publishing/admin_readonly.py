"""Django admin is read-only unless settings.DJANGO_ADMIN_READONLY is False (contract WS5.1).

The setting defaults to `not DEBUG`. It is read at call time so tests can toggle it.
"""
from django.conf import settings


def _readonly():
    return getattr(settings, "DJANGO_ADMIN_READONLY", not settings.DEBUG)


def make_admin_readonly():
    from django.contrib import admin

    def wrap(model_admin, name):
        original = getattr(model_admin, name)

        def checked(request, *args, **kwargs):
            if _readonly():
                return False
            return original(request, *args, **kwargs)

        setattr(model_admin, name, checked)

    for model_admin in list(admin.site._registry.values()):
        if getattr(model_admin, "_cms_readonly_wrapped", False):
            continue
        for name in ("has_add_permission", "has_change_permission", "has_delete_permission"):
            wrap(model_admin, name)
        model_admin._cms_readonly_wrapped = True
