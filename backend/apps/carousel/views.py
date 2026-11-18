from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.publishing.drf import CMSResourceMixin

from .models import HeroSlide, ProjectSlide
from .serializers import HeroSlideSerializer, ProjectSlideSerializer


class HeroSlideViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = HeroSlide.objects.all()
    serializer_class = HeroSlideSerializer


class ProjectSlideViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = ProjectSlide.objects.all()
    serializer_class = ProjectSlideSerializer
