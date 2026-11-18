from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.publishing.drf import CMSResourceMixin

from .models import Innovation, InnovationImage
from .serializers import InnovationImageSerializer, InnovationSerializer


class InnovationViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = Innovation.objects.prefetch_related("images").all()
    serializer_class = InnovationSerializer


class InnovationImageViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = InnovationImage.objects.all()
    serializer_class = InnovationImageSerializer
    filterset_fields = ["innovation"]
