from django.urls import path

from . import agent, views

cms_patterns = [
    path("pages/", views.PagesView.as_view(), name="cms-pages"),
    path("pages/<str:page_id>/", views.PageDetailView.as_view(), name="cms-page"),
    path("preview/<str:page_id>/", views.PreviewView.as_view(), name="cms-preview"),
    path("changes/", views.ChangesView.as_view(), name="cms-changes"),
    path("changes/discard/", views.DiscardView.as_view(), name="cms-discard"),
    path("review-requests/", views.ReviewRequestsView.as_view(), name="cms-review-requests"),
    path("publish/", views.PublishView.as_view(), name="cms-publish"),
    path("publish/<uuid:publish_id>/", views.PublishDetailView.as_view(), name="cms-publish-detail"),
    path("publish/<uuid:publish_id>/cancel/", views.PublishCancelView.as_view(), name="cms-publish-cancel"),
    path("snapshots/", views.SnapshotsView.as_view(), name="cms-snapshots"),
    path("snapshots/<int:pk>/restore/", views.SnapshotRestoreView.as_view(), name="cms-snapshot-restore"),
    path("backup/", views.BackupView.as_view(), name="cms-backup"),
    path("backup/restore/", views.BackupRestoreView.as_view(), name="cms-backup-restore"),
    path("audit/", views.AuditView.as_view(), name="cms-audit"),
    path("upload-links/", views.UploadLinksView.as_view(), name="cms-upload-links"),
    path("upload/<str:token>/", views.upload_page, name="cms-upload"),
]

agent_patterns = [
    path("next/", agent.next_build, name="agent-next"),
    path("builds/<uuid:publish_id>.tar.gz", agent.download_build, name="agent-build"),
    path("status/", agent.post_status, name="agent-status"),
]
