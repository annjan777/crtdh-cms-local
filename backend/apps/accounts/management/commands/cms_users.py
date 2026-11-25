"""List CMS users and their roles, or make one user an admin.

    python manage.py cms_users                      # who can sign in, and with which role
    python manage.py cms_users --make-admin NAME    # give NAME the admin role

On the CIC server: ~/.crtdh/crtdh users   and   ~/.crtdh/crtdh make-admin NAME
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.roles import ADMIN, user_roles


class Command(BaseCommand):
    help = "List CMS users and their roles, or give one user the admin role."

    def add_arguments(self, parser):
        parser.add_argument("--make-admin", metavar="USERNAME", help="Give this user the admin role.")

    def handle(self, *args, **opts):
        User = get_user_model()
        name = opts.get("make_admin")
        if name:
            user = User.objects.filter(username__iexact=name).first()
            if user is None:
                raise CommandError(f"No user called '{name}'. Run without options to see the list.")
            group, _ = Group.objects.get_or_create(name=ADMIN)
            user.groups.add(group)
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])
                self.stdout.write(f"{user.username} was switched off; switched back on.")
            self.stdout.write(self.style.SUCCESS(f"{user.username} now has the admin role. Sign out and back in."))
            return

        users = User.objects.order_by("username").prefetch_related("groups")
        if not users:
            self.stdout.write("No users yet.")
            return
        width = max(len(u.username) for u in users)
        for u in users:
            roles = user_roles(u)
            role = roles[-1] if roles else "no role"
            notes = []
            if u.is_superuser:
                notes.append("superuser")
            if not u.is_active:
                notes.append("switched off, cannot sign in")
            extra = f"  ({', '.join(notes)})" if notes else ""
            self.stdout.write(f"{u.username.ljust(width)}  {role}{extra}")
