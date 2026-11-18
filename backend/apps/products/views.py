from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.publishing.drf import CMSResourceMixin

from .models import Product, ProductImage, ProductPartner
from .serializers import ProductImageSerializer, ProductPartnerSerializer, ProductSerializer


class ProductViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = Product.objects.prefetch_related("images", "partners").all()
    serializer_class = ProductSerializer


class ProductImageViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    filterset_fields = ["product"]


class ProductPartnerViewSet(CMSResourceMixin, ModelViewSet):
    """No `reorder` action: ProductPartner has no `order` field in the contract
    (id, product, name, logo only)."""

    queryset = ProductPartner.objects.all()
    serializer_class = ProductPartnerSerializer
    filterset_fields = ["product"]
