from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.publishing.drf import CMSResourceMixin

from .models import Enterprise
from .serializers import EnterpriseSerializer


class EnterpriseViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = Enterprise.objects.all()
    serializer_class = EnterpriseSerializer
