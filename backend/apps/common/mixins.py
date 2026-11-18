from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.publishing import content
from apps.publishing.audit import context_from_request
from apps.publishing.errors import CMSError


class ReorderMixin:
    """Adds `POST /<resource>/reorder/` to a ModelViewSet.

    Body: {"order": [id, id, id, ...]} — the full ordered list of primary keys for this resource's (possibly
    filtered) queryset. Each row's `order` becomes its position (from 0); rows that move get a version bump and
    an audit entry (apps.publishing.content.reorder). Any id outside the queryset → 400 and nothing changes.
    """

    reorder_field = "order"

    @action(detail=False, methods=["post"])
    def reorder(self, request, *args, **kwargs):
        ids = request.data.get("order")
        if not isinstance(ids, list) or not ids:
            raise CMSError("CMS_VALIDATION", "Expected a non-empty list at `order`.", field="order")
        try:
            ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            raise CMSError("CMS_VALIDATION", "`order` must be a list of integer ids.", field="order") from None

        queryset = self.filter_queryset(self.get_queryset())
        existing_ids = set(queryset.values_list("pk", flat=True))
        if set(ids) != existing_ids or len(ids) != len(set(ids)):
            missing, unexpected = sorted(existing_ids - set(ids)), sorted(set(ids) - existing_ids)
            raise CMSError("CMS_VALIDATION",
                           f"`order` must list exactly the ids of this list (missing {missing}, unexpected {unexpected}).",
                           field="order")

        content.reorder(content.resource_for_model(queryset.model), ids, ctx=context_from_request(request),
                        queryset=queryset, field=self.reorder_field)
        return Response({"detail": "Order updated.", "order": ids}, status=status.HTTP_200_OK)
