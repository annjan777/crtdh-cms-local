"""
Thin convenience wrapper around Django's built-in `createsuperuser` for creating
a staff account for the admin SPA.

The project uses Django's default `User` model as-is (with its built-in
`is_staff` flag), so `python manage.py createsuperuser` already works fine and
needs no customization — this command just documents that fact and gives staff
creation a more obviously-named entry point.

Usage:
    python manage.py createstaffuser --username alice --email alice@example.com
    (then follow the interactive password prompt, same as createsuperuser)

Never script a password on the command line. For role-limited CMS users use the
user-admin API (POST /api/v1/auth/users/) or, in local dev only, `create_dev_users`.
"""

from django.contrib.auth.management.commands.createsuperuser import (
    Command as CreateSuperuserCommand,
)


class Command(CreateSuperuserCommand):
    help = (
        "Create a staff account for the admin SPA (alias for createsuperuser — "
        "the resulting user has is_staff=is_superuser=True). For a staff-but-not-"
        "superuser account, use the Django shell instead; see this file's docstring."
    )
