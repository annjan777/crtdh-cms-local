"""URLconf used by the Django part of the MCP process: OAuth + metadata only."""

from apps.oauth.urls import oauth_urlpatterns, wellknown_urlpatterns

urlpatterns = [*wellknown_urlpatterns, *oauth_urlpatterns]
