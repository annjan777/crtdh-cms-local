from django.contrib import admin

from .models import AboutPage, FocusArea, HomePage, NavItem, NewsItem, ObjectiveRow, SiteSettings, TimelineEntry

admin.site.register(SiteSettings)
admin.site.register(AboutPage)
admin.site.register(HomePage)
admin.site.register(NavItem)
admin.site.register(NewsItem)
admin.site.register(FocusArea)
admin.site.register(ObjectiveRow)
admin.site.register(TimelineEntry)
