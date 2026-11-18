from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.publishing.drf import CMSResourceMixin

from .models import TeamCategory, TeamMember
from .serializers import TeamCategorySerializer, TeamMemberSerializer


class TeamCategoryViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = TeamCategory.objects.all()
    serializer_class = TeamCategorySerializer


class TeamMemberViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = TeamMember.objects.select_related("category").all()
    serializer_class = TeamMemberSerializer
    filterset_fields = ["category"]
