from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.common.permissions import IsAdminOrReadOnly

from .models import HeroSlide, ProjectSlide
from .serializers import HeroSlideSerializer, ProjectSlideSerializer


class HeroSlideViewSet(ReorderMixin, ModelViewSet):
    queryset = HeroSlide.objects.all()
    serializer_class = HeroSlideSerializer
    permission_classes = [IsAdminOrReadOnly]


class ProjectSlideViewSet(ReorderMixin, ModelViewSet):
    queryset = ProjectSlide.objects.all()
    serializer_class = ProjectSlideSerializer
    permission_classes = [IsAdminOrReadOnly]
