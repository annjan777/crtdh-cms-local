from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.publishing.drf import CMSResourceMixin

from .models import Equipment
from .serializers import EquipmentSerializer


class EquipmentViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
