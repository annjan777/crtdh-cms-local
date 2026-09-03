from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.common.permissions import IsAdminOrReadOnly

from .models import Innovation, InnovationImage
from .serializers import InnovationImageSerializer, InnovationSerializer


class InnovationViewSet(ReorderMixin, ModelViewSet):
    queryset = Innovation.objects.prefetch_related("images").all()
    serializer_class = InnovationSerializer
    permission_classes = [IsAdminOrReadOnly]


class InnovationImageViewSet(ReorderMixin, ModelViewSet):
    queryset = InnovationImage.objects.all()
    serializer_class = InnovationImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["innovation"]
