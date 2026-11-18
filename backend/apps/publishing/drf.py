"""DRF glue: resource viewsets and singleton views write only through apps.publishing.content."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import content
from .audit import context_from_request
from .permissions import ContentPermission


class CMSResourceMixin:
    """Mix into a ModelViewSet: create/update/delete go through content.* (versions + audit)."""

    permission_classes = [ContentPermission]

    @property
    def resource(self):
        return content.resource_for_model(self.get_queryset().model)

    def create(self, request, *args, **kwargs):
        obj = content.create_item(self.resource, request.data, ctx=context_from_request(request),
                                  serializer_class=self.get_serializer_class(), context=self.get_serializer_context())
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        obj = content.update_item(self.resource, instance.pk, request.data, ctx=context_from_request(request),
                                  expected_version=request.data.get("expected_version"),
                                  partial=kwargs.get("partial", False),
                                  serializer_class=self.get_serializer_class(), context=self.get_serializer_context())
        return Response(self.get_serializer(obj).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        expected = request.data.get("expected_version") if hasattr(request, "data") else None
        content.delete_item(self.resource, instance.pk, ctx=context_from_request(request), expected_version=expected)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SingletonView(APIView):
    """GET/PATCH/PUT for a pk=1 singleton (site-settings, about-page, home-page)."""

    permission_classes = [ContentPermission]
    model = None
    serializer_class = None

    @property
    def resource(self):
        return content.resource_for_model(self.model)

    def get(self, request):
        obj = self.model.load()
        return Response(self.serializer_class(obj, context={"request": request}).data)

    def patch(self, request):
        self.model.load()
        obj = content.update_item(self.resource, 1, request.data, ctx=context_from_request(request),
                                  expected_version=request.data.get("expected_version"), partial=True,
                                  serializer_class=self.serializer_class, context={"request": request})
        return Response(self.serializer_class(obj, context={"request": request}).data)

    def put(self, request):
        return self.patch(request)
