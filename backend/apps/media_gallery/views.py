from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.common.permissions import IsAdminOrReadOnly

from .models import GalleryImage, MediaCoverageLink, MediaEvent, MediaEventImage
from .serializers import (
    GalleryImageSerializer,
    MediaCoverageLinkSerializer,
    MediaEventImageSerializer,
    MediaEventSerializer,
)


class MediaEventViewSet(ReorderMixin, ModelViewSet):
    queryset = MediaEvent.objects.prefetch_related("images").all()
    serializer_class = MediaEventSerializer
    permission_classes = [IsAdminOrReadOnly]


class MediaEventImageViewSet(ReorderMixin, ModelViewSet):
    queryset = MediaEventImage.objects.all()
    serializer_class = MediaEventImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["event"]


class MediaCoverageLinkViewSet(ReorderMixin, ModelViewSet):
    queryset = MediaCoverageLink.objects.all()
    serializer_class = MediaCoverageLinkSerializer
    permission_classes = [IsAdminOrReadOnly]


class GalleryImageViewSet(ReorderMixin, ModelViewSet):
    queryset = GalleryImage.objects.all()
    serializer_class = GalleryImageSerializer
    permission_classes = [IsAdminOrReadOnly]
