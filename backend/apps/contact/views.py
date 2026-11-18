import logging

from django.conf import settings
from django.core.mail import EmailMessage
from rest_framework import mixins, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from apps.accounts.roles import IsPublisher
from apps.common.errors import CMSError
from apps.common.middleware import client_ip
from apps.common.throttles import IPScopedThrottle

from . import turnstile
from .models import ContactMessage
from .serializers import ContactMessageCreateSerializer, ContactMessageSerializer

logger = logging.getLogger("crtdh.security")
ACCEPTED = {"status": "received", "message": "Thanks, we have your message and will reply by email."}


class ContactCreateView(APIView):
    """POST /api/v1/contact/ - the only public write. No session, no cookies (cross-origin from the static site)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [IPScopedThrottle]
    throttle_scope = "contact"
    http_method_names = ["post", "options"]

    def post(self, request):
        ser = ContactMessageCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if data.get("website"):  # honeypot filled: pretend success, store nothing
            logger.info("contact honeypot hit ip=%s", client_ip(request))
            return Response(ACCEPTED, status=status.HTTP_201_CREATED)
        if not turnstile.verify(data.get("turnstile_token"), client_ip(request)):
            raise CMSError("CMS_VALIDATION", "We could not confirm you are not a bot.",
                           fix="Reload the page and complete the check again.", field="turnstile_token",
                           retryable=True)
        msg = ser.save()
        self._notify(msg)
        return Response(ACCEPTED, status=status.HTTP_201_CREATED)

    def _notify(self, msg):
        to = settings.CONTACT_NOTIFY_EMAIL
        if not to:
            return
        body = (
            "A new message arrived through the CRTDH website contact form.\n"
            f"Read it in the CMS: Contact messages, #{msg.pk}.\n\n"
            "The sender's details are kept in the CMS only and are deleted automatically "
            f"after {settings.CONTACT_RETENTION_DAYS} days.\n"
        )
        try:
            EmailMessage("New CRTDH contact message", body, settings.DEFAULT_FROM_EMAIL, [to]).send()
        except Exception:
            logger.exception("contact notification email failed id=%s", msg.pk)


class ContactMessageViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                            GenericViewSet):
    """/api/v1/contact-messages/ - publishers and admins: list/retrieve/delete (erasure on request)."""

    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [IsPublisher]
