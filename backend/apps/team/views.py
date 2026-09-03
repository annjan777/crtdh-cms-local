from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.common.permissions import IsAdminOrReadOnly

from .models import TeamCategory, TeamMember
from .serializers import TeamCategorySerializer, TeamMemberSerializer


class TeamCategoryViewSet(ReorderMixin, ModelViewSet):
    queryset = TeamCategory.objects.all()
    serializer_class = TeamCategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class TeamMemberViewSet(ReorderMixin, ModelViewSet):
    queryset = TeamMember.objects.select_related("category").all()
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["category"]
