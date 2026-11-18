from rest_framework.viewsets import ModelViewSet

from apps.common.mixins import ReorderMixin
from apps.publishing.drf import CMSResourceMixin, SingletonView

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


class SiteSettingsView(SingletonView):
    """Singleton resource: GET/PATCH /api/v1/site-settings/ — always the single row (pk=1)."""

    model = SiteSettings
    serializer_class = SiteSettingsSerializer


class AboutPageView(SingletonView):
    """Singleton resource: GET/PATCH /api/v1/about-page/ — always the single row (pk=1)."""

    model = AboutPage
    serializer_class = AboutPageSerializer


class HomePageView(SingletonView):
    """Singleton resource: GET/PATCH /api/v1/home-page/ — always the single row (pk=1)."""

    model = HomePage
    serializer_class = HomePageSerializer


class NavItemViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = NavItem.objects.all()
    serializer_class = NavItemSerializer


class NewsItemViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = NewsItem.objects.all()
    serializer_class = NewsItemSerializer


class FocusAreaViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = FocusArea.objects.all()
    serializer_class = FocusAreaSerializer


class ObjectiveRowViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = ObjectiveRow.objects.all()
    serializer_class = ObjectiveRowSerializer


class TimelineEntryViewSet(CMSResourceMixin, ReorderMixin, ModelViewSet):
    queryset = TimelineEntry.objects.all()
    serializer_class = TimelineEntrySerializer
