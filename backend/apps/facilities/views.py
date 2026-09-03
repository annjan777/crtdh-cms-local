from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.common.permissions import IsAdminOrReadOnly

from .models import Equipment
from .serializers import EquipmentSerializer


class EquipmentViewSet(ReorderMixin, ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [IsAdminOrReadOnly]
