from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.common.permissions import IsAdminOrReadOnly

from .models import Service
from .serializers import ServiceSerializer


class ServiceViewSet(ReorderMixin, ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminOrReadOnly]
