from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.common.permissions import IsAdminOrReadOnly

from .models import AboutPage, FocusArea, HomePage, NavItem, NewsItem, ObjectiveRow, SiteSettings, TimelineEntry
from .serializers import (
    AboutPageSerializer,
    FocusAreaSerializer,
    HomePageSerializer,
    NavItemSerializer,
    NewsItemSerializer,
    ObjectiveRowSerializer,
    SiteSettingsSerializer,
    TimelineEntrySerializer,
)


class SiteSettingsView(APIView):
    """Singleton resource: GET/PATCH /api/v1/site-settings/ — always the single row (pk=1)."""

    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        obj = SiteSettings.load()
        serializer = SiteSettingsSerializer(obj, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        obj = SiteSettings.load()
        serializer = SiteSettingsSerializer(
            obj, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def put(self, request):
        return self.patch(request)


class AboutPageView(APIView):
    """Singleton resource: GET/PATCH /api/v1/about-page/ — always the single row (pk=1)."""

    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        obj = AboutPage.load()
        serializer = AboutPageSerializer(obj, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        obj = AboutPage.load()
        serializer = AboutPageSerializer(obj, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def put(self, request):
        return self.patch(request)


class HomePageView(APIView):
    """Singleton resource: GET/PATCH /api/v1/home-page/ — always the single row (pk=1)."""

    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        obj = HomePage.load()
        serializer = HomePageSerializer(obj, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        obj = HomePage.load()
        serializer = HomePageSerializer(obj, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def put(self, request):
        return self.patch(request)


class NavItemViewSet(ReorderMixin, ModelViewSet):
    queryset = NavItem.objects.all()
    serializer_class = NavItemSerializer
    permission_classes = [IsAdminOrReadOnly]


class NewsItemViewSet(ReorderMixin, ModelViewSet):
    queryset = NewsItem.objects.all()
    serializer_class = NewsItemSerializer
    permission_classes = [IsAdminOrReadOnly]


class FocusAreaViewSet(ReorderMixin, ModelViewSet):
    queryset = FocusArea.objects.all()
    serializer_class = FocusAreaSerializer
    permission_classes = [IsAdminOrReadOnly]


class ObjectiveRowViewSet(ReorderMixin, ModelViewSet):
    queryset = ObjectiveRow.objects.all()
    serializer_class = ObjectiveRowSerializer
    permission_classes = [IsAdminOrReadOnly]


class TimelineEntryViewSet(ReorderMixin, ModelViewSet):
    queryset = TimelineEntry.objects.all()
    serializer_class = TimelineEntrySerializer
    permission_classes = [IsAdminOrReadOnly]
