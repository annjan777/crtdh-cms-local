"""Dev/test only: create one CMS user per role for E2E, preprod rehearsal and simulated UAT.

Refuses to run unless CRTDH_ALLOW_TEST_SEED=1 is set in the environment, and refuses outright
when CRTDH_ENV=production without --rehearsal. The password comes from CRTDH_TEST_PASSWORD
(required, never defaulted, never written to disk by this command). Prints a JSON summary
(usernames, roles, TOTP secret if MFA enrolment is available) to stdout for the caller.
"""
import json
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.roles import ORDER

USERS = [
    ("erin_editor", "editor", "Erin", "Editor"),
    ("priya", "publisher", "Priya", "Publisher"),
    ("ada_admin", "admin", "Ada", "Admin"),
]


class Command(BaseCommand):
    help = "Create test users editor/publisher/admin (dev/test only; needs CRTDH_ALLOW_TEST_SEED=1)."

    def add_arguments(self, parser):
        parser.add_argument("--rehearsal", action="store_true",
                            help="allow under CRTDH_ENV=production for the local preprod rehearsal only")
        parser.add_argument("--no-mfa", action="store_true", help="do not enrol TOTP even if available")

    def handle(self, *args, **opts):
        if os.environ.get("CRTDH_ALLOW_TEST_SEED") != "1":
            raise CommandError("refusing: set CRTDH_ALLOW_TEST_SEED=1 (dev/test only)")
        if os.environ.get("CRTDH_ENV") == "production" and not opts["rehearsal"]:
            raise CommandError("refusing: CRTDH_ENV=production (use --rehearsal only for the local preprod rehearsal)")
        password = os.environ.get("CRTDH_TEST_PASSWORD")
        if not password or len(password) < 12:
            raise CommandError("CRTDH_TEST_PASSWORD must be set (12+ chars)")

        groups = {n: Group.objects.get_or_create(name=n)[0] for n in ORDER}
        enroll = None
        if not opts["no_mfa"]:
            try:
                from apps.accounts import mfa  # provided by backend-security
                enroll = getattr(mfa, "enroll_totp_for_test", None)
            except Exception:
                enroll = None
        out = {}
        User = get_user_model()
        for username, role, first, last in USERS:
            user, _ = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.test"})
            user.first_name, user.last_name, user.is_active = first, last, True
            user.set_password(password)
            user.save()
            user.groups.set([groups[role]])
            entry = {"role": role, "name": f"{first} {last}"}
            if enroll:
                entry["totp_secret"] = enroll(user)
            out[username] = entry
        self.stdout.write(json.dumps(out))
