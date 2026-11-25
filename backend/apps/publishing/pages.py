"""Public page ids (contract §2). Plain data, no Django imports, so models can use it for choices."""

PAGES = [
    ("home", "/", "Home"),
    ("about", "/about", "About"),
    ("team", "/team", "Team"),
    ("innovations", "/innovations", "Innovations"),
    ("facilities", "/facilities", "Facilities"),
    ("services", "/services", "Services"),
    ("product", "/product", "Product"),
    ("enterprises", "/enterprises", "Enterprises"),
    ("social-impact", "/social-impact", "Social Impact"),
    ("covid-19", "/covid-19", "Covid-19"),
    ("research", "/research", "Research"),
    ("research-translation", "/research-translation", "Research translation"),
    ("media", "/media", "Media"),
    ("contact", "/contact", "Contact"),
]

PAGE_CHOICES = [(pid, title) for pid, _path, title in PAGES]
PAGE_IDS = [pid for pid, _path, _title in PAGES]
