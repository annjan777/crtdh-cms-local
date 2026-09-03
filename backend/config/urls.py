"""
URL configuration for the CRTDH CMS backend.

Every resource path below matches API_CONTRACT.md exactly.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.views import MeView
from apps.carousel.views import HeroSlideViewSet, ProjectSlideViewSet
from apps.common.views import (
    DocumentViewSet,
    ImageGridBlockViewSet,
    ImageGridItemViewSet,
    VideoBlockViewSet,
)
from apps.contact.views import ContactCreateView, ContactMessageViewSet
from apps.core.views import (
    AboutPageView,
    FocusAreaViewSet,
    HomePageView,
    NavItemViewSet,
    NewsItemViewSet,
    ObjectiveRowViewSet,
    SiteSettingsView,
    TimelineEntryViewSet,
)
from apps.enterprises.views import EnterpriseViewSet
from apps.facilities.views import EquipmentViewSet
from apps.innovations.views import InnovationImageViewSet, InnovationViewSet
from apps.media_gallery.views import (
    GalleryImageViewSet,
    MediaCoverageLinkViewSet,
    MediaEventImageViewSet,
    MediaEventViewSet,
)
from apps.products.views import ProductImageViewSet, ProductPartnerViewSet, ProductViewSet
from apps.services.views import ServiceViewSet
from apps.team.views import TeamCategoryViewSet, TeamMemberViewSet

router = DefaultRouter()

# core
router.register("nav-items", NavItemViewSet, basename="nav-item")
router.register("news-items", NewsItemViewSet, basename="news-item")
router.register("focus-areas", FocusAreaViewSet, basename="focus-area")
router.register("objective-rows", ObjectiveRowViewSet, basename="objective-row")
router.register("timeline-entries", TimelineEntryViewSet, basename="timeline-entry")

# carousel
router.register("hero-slides", HeroSlideViewSet, basename="hero-slide")
router.register("project-slides", ProjectSlideViewSet, basename="project-slide")

# team
router.register("team-categories", TeamCategoryViewSet, basename="team-category")
router.register("team-members", TeamMemberViewSet, basename="team-member")

# facilities
router.register("equipment", EquipmentViewSet, basename="equipment")

# services
router.register("services", ServiceViewSet, basename="service")

# innovations
router.register("innovations", InnovationViewSet, basename="innovation")
router.register("innovation-images", InnovationImageViewSet, basename="innovation-image")

# products
router.register("products", ProductViewSet, basename="product")
router.register("product-images", ProductImageViewSet, basename="product-image")
router.register("product-partners", ProductPartnerViewSet, basename="product-partner")

# enterprises
router.register("enterprises", EnterpriseViewSet, basename="enterprise")

# media / gallery
router.register("media-events", MediaEventViewSet, basename="media-event")
router.register("media-event-images", MediaEventImageViewSet, basename="media-event-image")
router.register("media-coverage-links", MediaCoverageLinkViewSet, basename="media-coverage-link")
router.register("gallery-images", GalleryImageViewSet, basename="gallery-image")

# common (generic reusable content types)
router.register("image-grid-blocks", ImageGridBlockViewSet, basename="image-grid-block")
router.register("image-grid-items", ImageGridItemViewSet, basename="image-grid-item")
router.register("video-blocks", VideoBlockViewSet, basename="video-block")
router.register("documents", DocumentViewSet, basename="document")

# contact (admin-facing read/delete side; public POST is a separate APIView below)
router.register("contact-messages", ContactMessageViewSet, basename="contact-message")

api_v1_patterns = [
    path("", include(router.urls)),
    path("site-settings/", SiteSettingsView.as_view(), name="site-settings"),
    path("about-page/", AboutPageView.as_view(), name="about-page"),
    path("home-page/", HomePageView.as_view(), name="home-page"),
    path("contact/", ContactCreateView.as_view(), name="contact-create"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1_patterns)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
