"""Local development only: creates dev-editor / dev-publisher / dev-admin with
random passwords printed once. Refuses to run unless DEBUG is true."""
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts import mfa
from apps.accounts.roles import ORDER
from apps.accounts.users import set_role


class Command(BaseCommand):
    help = "DEV ONLY: create editor/publisher/admin test users with random passwords (printed once)."

    def add_arguments(self, parser):
        parser.add_argument("--with-totp", action="store_true",
                            help="also enrol TOTP and print each secret (for automated local tests)")

    def handle(self, *args, **opts):
        if not settings.DEBUG or settings.CRTDH_ENV == "production":
            raise CommandError("create_dev_users only runs with DEBUG=True outside production.")
        User = get_user_model()
        for role in ORDER:
            username = f"dev-{role}"
            password = secrets.token_urlsafe(18)
            user, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@localhost"})
            user.set_password(password)
            user.is_active = True
            user.save()
            set_role(user, role)
            line = f"{username:15} role={role:9} password={password}"
            if opts["with_totp"]:
                secret = mfa.start_enrolment(user)["secret"]
                user.security.totp_confirmed_at = user.date_joined
                user.security.save(update_fields=["totp_confirmed_at"])
                line += f" totp_secret={secret}"
            self.stdout.write(line + ("" if created else "  (existing user, password reset)"))
        self.stdout.write(self.style.WARNING("Shown once. These are local test accounts; never use them on a server."))
