"""Stand-in section registry, shaped like contracts §2.

TODO(integration, backend-core): delete this file and read `apps.publishing.registry`
instead (cms.registry_pages()). Field lists are derived from the models here; the core
registry declares them explicitly.
"""

PAGES = [
    {"id": "home", "path": "/", "title": "Home", "sections": [
        {"id": "home.hero", "label": "Hero", "kind": "collection", "resource": "hero-slides"},
        {"id": "home.news", "label": "News ticker", "kind": "collection", "resource": "news-items"},
        {"id": "home.projects", "label": "Project slides", "kind": "collection", "resource": "project-slides"},
        {"id": "home.about", "label": "Home page sections", "kind": "singleton", "resource": "home-page"},
    ]},
    {"id": "about", "path": "/about", "title": "About", "sections": [
        {"id": "about.text", "label": "About text", "kind": "singleton", "resource": "about-page"},
        {"id": "about.focus", "label": "Focus areas", "kind": "collection", "resource": "focus-areas"},
        {"id": "about.objectives", "label": "Objectives", "kind": "collection", "resource": "objective-rows"},
        {"id": "about.timeline", "label": "Timeline", "kind": "collection", "resource": "timeline-entries"},
    ]},
    {"id": "team", "path": "/team", "title": "Team", "sections": [
        {"id": "team.members", "label": "Team members", "kind": "collection", "resource": "team-members"},
    ]},
    {"id": "innovations", "path": "/innovations", "title": "Innovations", "sections": [
        {"id": "innovations.list", "label": "Innovations", "kind": "collection", "resource": "innovations"},
    ]},
    {"id": "facilities", "path": "/facilities", "title": "Facilities", "sections": [
        {"id": "facilities.equipment", "label": "Equipment", "kind": "collection", "resource": "equipment"},
        {"id": "facilities.grids", "label": "Photo grids", "kind": "collection", "resource": "image-grid-blocks",
         "filter": {"page": "facilities"}},
    ]},
    {"id": "services", "path": "/services", "title": "Services", "sections": [
        {"id": "services.list", "label": "Services", "kind": "collection", "resource": "services"},
    ]},
    {"id": "product", "path": "/product", "title": "Product", "sections": [
        {"id": "product.list", "label": "Products", "kind": "collection", "resource": "products"},
    ]},
    {"id": "enterprises", "path": "/enterprises", "title": "Enterprises", "sections": [
        {"id": "enterprises.list", "label": "Enterprises", "kind": "collection", "resource": "enterprises"},
    ]},
    {"id": "social-impact", "path": "/social-impact", "title": "Social Impact", "sections": [
        {"id": "social-impact.grids", "label": "Photo grids", "kind": "collection", "resource": "image-grid-blocks",
         "filter": {"page": "social-impact"}},
        {"id": "social-impact.videos", "label": "Videos", "kind": "collection", "resource": "video-blocks",
         "filter": {"page": "social-impact"}},
    ]},
    {"id": "covid-19", "path": "/covid-19", "title": "Covid-19", "sections": [
        {"id": "covid-19.grids", "label": "Photo grids", "kind": "collection", "resource": "image-grid-blocks",
         "filter": {"page": "covid-19"}},
    ]},
    {"id": "media", "path": "/media", "title": "Media", "sections": [
        {"id": "media.events", "label": "Events and camps", "kind": "collection", "resource": "media-events"},
        {"id": "media.coverage", "label": "Press coverage", "kind": "collection", "resource": "media-coverage-links"},
        {"id": "media.gallery", "label": "Gallery", "kind": "collection", "resource": "gallery-images"},
    ]},
    {"id": "contact", "path": "/contact", "title": "Contact", "sections": [
        {"id": "contact.settings", "label": "Contact details", "kind": "singleton", "resource": "site-settings"},
    ]},
]

# Field overrides on top of the model-derived fields: resource -> field name -> extra keys.
FIELD_OVERRIDES = {
    "hero-slides": {"image": {"required": True, "min_width": 1600}, "heading": {"max": 60}},
    "team-members": {"name": {"required": True}, "photo": {"min_width": 600}},
    "media-events": {"title": {"required": True}},
    "news-items": {"text": {"required": True}},
    "innovations": {"body": {"type": "richtext"}},
}

# Photos that belong to a collection row (child rows with an image + caption).
GALLERIES = {
    "media-events": {"name": "photos", "child": "media-event-images", "fk": "event"},
    "innovations": {"name": "photos", "child": "innovation-images", "fk": "innovation"},
    "image-grid-blocks": {"name": "photos", "child": "image-grid-items", "fk": "block"},
}

# Fields MCP never edits directly (visibility has hide_*, order has reorder, slugs are derived).
HIDDEN_FIELDS = {"id", "order", "is_published", "slug"}
