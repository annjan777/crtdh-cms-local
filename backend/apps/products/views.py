from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.common.permissions import IsAdminOrReadOnly

from .models import Product, ProductImage, ProductPartner
from .serializers import ProductImageSerializer, ProductPartnerSerializer, ProductSerializer


class ProductViewSet(ReorderMixin, ModelViewSet):
    queryset = Product.objects.prefetch_related("images", "partners").all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductImageViewSet(ReorderMixin, ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["product"]


class ProductPartnerViewSet(ModelViewSet):
    """No `reorder` action: ProductPartner has no `order` field in the contract
    (id, product, name, logo only)."""

    queryset = ProductPartner.objects.all()
    serializer_class = ProductPartnerSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["product"]
