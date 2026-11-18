from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.publishing.drf import CMSResourceMixin

from .models import Service
from .serializers import ServiceSerializer


class ServiceViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
