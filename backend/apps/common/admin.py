from django.contrib import admin

from .models import Document, ImageGridBlock, ImageGridItem, VideoBlock

admin.site.register(ImageGridBlock)
admin.site.register(ImageGridItem)
admin.site.register(VideoBlock)
admin.site.register(Document)
