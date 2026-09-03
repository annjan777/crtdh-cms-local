from django.contrib import admin

from .models import GalleryImage, MediaCoverageLink, MediaEvent, MediaEventImage

admin.site.register(MediaEvent)
admin.site.register(MediaEventImage)
admin.site.register(MediaCoverageLink)
admin.site.register(GalleryImage)
