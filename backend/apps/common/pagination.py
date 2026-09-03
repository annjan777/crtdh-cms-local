from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500


class NonCollidingPagePagination(StandardResultsPagination):
    """Same as StandardResultsPagination, but paginates on `?p=` instead of
    `?page=`. Used by viewsets whose model has its own `page` field
    (ImageGridBlock, VideoBlock: "which site page this belongs to", e.g.
    "facilities") — the API contract filters those with `?page=<slug>`,
    which DRF's default PageNumberPagination would otherwise swallow as a
    (non-integer, so 404 "Invalid page") pagination page number."""

    page_query_param = "p"
