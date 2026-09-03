from rest_framework.viewsets import ModelViewSet

from .mixins import ReorderMixin
from .models import Document, ImageGridBlock, ImageGridItem, VideoBlock
from .pagination import NonCollidingPagePagination
from .permissions import IsAdminOrReadOnly
from .serializers import (
    DocumentSerializer,
    ImageGridBlockSerializer,
    ImageGridItemSerializer,
    VideoBlockSerializer,
)


class ImageGridBlockViewSet(ModelViewSet):
    """No `reorder` action: ImageGridBlock has no `order` field in the contract
    (page/section_title/anchor_slug/items only) — its items are ordered instead."""

    queryset = ImageGridBlock.objects.prefetch_related("items").all()
    serializer_class = ImageGridBlockSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["page"]
    # `page` here is a model field (which site page this block belongs to),
    # not a pagination cursor — see NonCollidingPagePagination's docstring.
    pagination_class = NonCollidingPagePagination


class ImageGridItemViewSet(ReorderMixin, ModelViewSet):
    queryset = ImageGridItem.objects.all()
    serializer_class = ImageGridItemSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["block"]


class VideoBlockViewSet(ReorderMixin, ModelViewSet):
    queryset = VideoBlock.objects.all()
    serializer_class = VideoBlockSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["page"]
    pagination_class = NonCollidingPagePagination


class DocumentViewSet(ReorderMixin, ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["category"]
