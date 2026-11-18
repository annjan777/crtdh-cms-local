from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q

from apps.accounts.roles import ADMIN, PUBLISHER

from .models import ReviewRequest


def publisher_emails():
    users = (get_user_model().objects.filter(is_active=True)
             .filter(Q(is_superuser=True) | Q(groups__name__in=[PUBLISHER, ADMIN])).exclude(email="").distinct())
    return sorted({u.email for u in users})


def request_review(user, note="", *, ctx=None):
    from .changes import pending_changes

    rr = ReviewRequest.objects.create(requested_by=user, note=(note or "")[:2000])
    pending = pending_changes()
    who = (user.get_full_name() or user.get_username()) if user else "Someone"
    via = " (through Claude)" if ctx is not None and getattr(ctx, "channel", "") == "mcp" else ""
    lines = [f"{who}{via} asked for a review of {pending['count']} unpublished change(s) on the CRTDH site.", ""]
    if note:
        lines += [f"Note: {note}", ""]
    for page in pending["pages"]:
        lines.append(f"- {page['page']}: {len(page['changes'])} change(s)")
    lines += ["", f"Review and publish: {settings.CMS_PUBLIC_URL.rstrip('/')}/review"]
    recipients = publisher_emails()
    if recipients:
        send_mail(f"CRTDH: review requested by {who}", "\n".join(lines), None, recipients, fail_silently=False)
    return rr
