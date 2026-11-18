from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.publishing.drf import CMSResourceMixin

from .models import GalleryImage, MediaCoverageLink, MediaEvent, MediaEventImage
from .serializers import (
    GalleryImageSerializer,
    MediaCoverageLinkSerializer,
    MediaEventImageSerializer,
    MediaEventSerializer,
)


class MediaEventViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = MediaEvent.objects.prefetch_related("images").all()
    serializer_class = MediaEventSerializer


class MediaEventImageViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = MediaEventImage.objects.all()
    serializer_class = MediaEventImageSerializer
    filterset_fields = ["event"]


class MediaCoverageLinkViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = MediaCoverageLink.objects.all()
    serializer_class = MediaCoverageLinkSerializer


class GalleryImageViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = GalleryImage.objects.all()
    serializer_class = GalleryImageSerializer
