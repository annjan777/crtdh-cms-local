from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.publishing import content
from apps.publishing.audit import context_from_request
from apps.publishing.errors import CMSError


class ReorderMixin:
    """Adds `POST /<resource>/reorder/` to a ModelViewSet.

    Body: {"order": [id, id, id, ...]} — the full ordered list of primary keys for this resource's (possibly
    filtered) queryset, or of one sibling group (rows sharing a parent such as `innovation`, or a `page`). Each row's `order` becomes its position (from 0); rows that move get a version bump and
    an audit entry (apps.publishing.content.reorder). Any id outside the queryset → 400 and nothing changes.
    """

    reorder_field = "order"
    group_fields = ("innovation", "product", "event", "block", "page", "category")

    def _sibling_group(self, queryset, ids):
        """{field: value} when every id shares one parent/page (the admin sends one child list at a time)."""
        names = {f.attname: f.name for f in queryset.model._meta.concrete_fields}
        for name in self.group_fields:
            attname = next((a for a, n in names.items() if n == name), None)
            if attname is None:
                continue
            values = set(queryset.filter(pk__in=ids).values_list(attname, flat=True))
            if len(values) == 1:
                return {attname: values.pop()}
        return None

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
        unexpected = sorted(set(ids) - existing_ids)
        if unexpected or len(ids) != len(set(ids)):
            raise CMSError("CMS_VALIDATION", f"`order` has unknown or repeated ids ({unexpected or 'repeated'}).",
                           field="order")
        group = self._sibling_group(queryset, ids)
        if group is not None:
            queryset = queryset.filter(**group)  # a child list (photos of one innovation, one page's videos)
            existing_ids = set(queryset.values_list("pk", flat=True))
        if set(ids) != existing_ids:
            missing = sorted(existing_ids - set(ids))
            raise CMSError("CMS_VALIDATION", f"`order` must list every item of this list (missing {missing}).",
                           field="order")

        content.reorder(content.resource_for_model(queryset.model), ids, ctx=context_from_request(request),
                        queryset=queryset, field=self.reorder_field)
        return Response({"detail": "Order updated.", "order": ids}, status=status.HTTP_200_OK)
