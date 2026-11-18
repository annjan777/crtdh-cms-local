from django.db import models
from apps.common.versioning import VersionedModel


class TeamCategory(VersionedModel):
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class TeamMember(VersionedModel):
    category = models.ForeignKey(TeamCategory, related_name="members", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    photo = models.ImageField(upload_to="team_members/", blank=True, null=True)
    # Shown on the public Team page when filled in; the admin Team editor already had inputs for these.
    designation = models.CharField(max_length=255, blank=True, default="")
    institution = models.CharField(max_length=255, blank=True, default="Indian Institute of Technology Kharagpur")
    description = models.TextField(blank=True, default="")
    is_published = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name
