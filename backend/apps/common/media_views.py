import mimetypes

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse
from django.utils._os import safe_join
from rest_framework.views import APIView

from apps.accounts.roles import IsEditor

from .errors import CMSError

INLINE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif"}


class MediaFileView(APIView):
    """GET /api/v1/media/<path> - private media for signed-in CMS users only."""

    permission_classes = [IsEditor]

    def get(self, request, path):
        try:
            full = safe_join(settings.MEDIA_ROOT, path)
            fh = open(full, "rb")
        except (ValueError, OSError, SuspiciousFileOperation):
            raise CMSError("CMS_NOT_FOUND", "File not found.", fix="Re-upload the file.")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        inline = ctype in INLINE_TYPES
        resp = FileResponse(fh, content_type=ctype if inline or ctype == "application/pdf" else "application/octet-stream",
                            as_attachment=not inline)
        resp["Content-Security-Policy"] = "default-src 'none'; sandbox"
        resp["Cache-Control"] = "private, max-age=300"
        return resp
