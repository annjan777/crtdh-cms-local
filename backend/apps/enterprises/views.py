from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.common.permissions import IsAdminOrReadOnly

from .models import Enterprise
from .serializers import EnterpriseSerializer


class EnterpriseViewSet(ReorderMixin, ModelViewSet):
    queryset = Enterprise.objects.all()
    serializer_class = EnterpriseSerializer
    permission_classes = [IsAdminOrReadOnly]
