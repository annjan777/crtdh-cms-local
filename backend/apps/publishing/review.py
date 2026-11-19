import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q

from apps.accounts.roles import ADMIN, PUBLISHER

from .models import ReviewRequest


def publisher_emails():
    users = (get_user_model().objects.filter(is_active=True)
             .filter(Q(is_superuser=True) | Q(groups__name__in=[PUBLISHER, ADMIN])).exclude(email="").distinct())
    return sorted({u.email for u in users})


log = logging.getLogger(__name__)

EMAIL_FAILED = "Review requested; the email to Publishers could not be sent."
NO_RECIPIENTS = "Review requested; no Publisher has an email address, so nobody was emailed."


class ReviewNotice:
    """Outcome of the Publisher email. `sent` is None until the request's transaction commits (the email is sent
    on commit, so a rolled-back request emails nobody), then True or False. A failed email never fails the request:
    the ReviewRequest row exists either way."""

    def __init__(self, recipients):
        self.recipients = recipients
        self.sent = None if recipients else False

    @property
    def message(self):
        if self.sent is False:
            return EMAIL_FAILED if self.recipients else NO_RECIPIENTS
        return ""

    def send(self, subject, body):
        try:
            send_mail(subject, body, None, self.recipients, fail_silently=False)
            self.sent = True
        except Exception:  # SMTP down, timeout, bad config: log it, keep the review request
            log.exception("review request email to %s Publisher(s) failed", len(self.recipients))
            self.sent = False


def request_review(user, note="", *, ctx=None):
    """Create a ReviewRequest and email the Publishers once it is committed. Returns the ReviewRequest with
    `.notice` (ReviewNotice)."""
    from .changes import pending_changes

    with transaction.atomic():
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
    rr.notice = notice = ReviewNotice(publisher_emails())
    if notice.recipients:
        subject, body = f"CRTDH: review requested by {who}", "\n".join(lines)
        transaction.on_commit(lambda: notice.send(subject, body))  # runs now when not inside a transaction
    return rr
