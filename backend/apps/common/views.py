from rest_framework.viewsets import ModelViewSet

from apps.publishing.drf import CMSResourceMixin

from .mixins import ReorderMixin
from .models import Document, ImageGridBlock, ImageGridItem, ImpactFigure, PageHero, ResearchStory, VideoBlock
from .pagination import NonCollidingPagePagination
from .serializers import (
    DocumentSerializer,
    ImageGridBlockSerializer,
    ImageGridItemSerializer,
    ImpactFigureSerializer,
    PageHeroSerializer,
    ResearchStorySerializer,
    VideoBlockSerializer,
)


class ImageGridBlockViewSet(CMSResourceMixin, ModelViewSet):
    """No `reorder` action: ImageGridBlock has no `order` field in the contract
    (page/section_title/anchor_slug/items only) — its items are ordered instead."""

    queryset = ImageGridBlock.objects.prefetch_related("items").all()
    serializer_class = ImageGridBlockSerializer
    filterset_fields = ["page"]
    # `page` here is a model field (which site page this block belongs to),
    # not a pagination cursor — see NonCollidingPagePagination's docstring.
    pagination_class = NonCollidingPagePagination


class ImageGridItemViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = ImageGridItem.objects.all()
    serializer_class = ImageGridItemSerializer
    filterset_fields = ["block"]


class VideoBlockViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = VideoBlock.objects.all()
    serializer_class = VideoBlockSerializer
    filterset_fields = ["page"]
    pagination_class = NonCollidingPagePagination


class DocumentViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    filterset_fields = ["category"]


class PageHeroViewSet(CMSResourceMixin, ModelViewSet):
    queryset = PageHero.objects.all()
    serializer_class = PageHeroSerializer
    filterset_fields = ["page"]
    pagination_class = NonCollidingPagePagination


class ResearchStoryViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = ResearchStory.objects.all()
    serializer_class = ResearchStorySerializer
    filterset_fields = ["page", "stage"]
    pagination_class = NonCollidingPagePagination


class ImpactFigureViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = ImpactFigure.objects.all()
    serializer_class = ImpactFigureSerializer
    filterset_fields = ["page"]
    pagination_class = NonCollidingPagePagination
