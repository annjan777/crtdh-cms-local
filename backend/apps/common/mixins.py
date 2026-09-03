from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response


class ReorderMixin:
    """Adds `POST /<resource>/reorder/` to a ModelViewSet.

    Body: {"order": [id, id, id, ...]} — the full ordered list of primary
    keys for this resource's queryset. Re-numbers each row's `order` field
    to match its position in the list (starting at 0). Staff-only (enforced
    by the viewset's permission_classes, same as any other write).

    All ids in the payload must belong to `self.get_queryset()`, otherwise
    the request is rejected with 400 and nothing is changed.
    """

    reorder_field = "order"

    @action(detail=False, methods=["post"])
    def reorder(self, request, *args, **kwargs):
        ids = request.data.get("order")
        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "Expected a non-empty list at `order`."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            return Response(
                {"detail": "`order` must be a list of integer ids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.filter_queryset(self.get_queryset())
        existing_ids = set(queryset.values_list("pk", flat=True))

        if set(ids) != existing_ids:
            return Response(
                {
                    "detail": (
                        "`order` must contain exactly the ids of this resource "
                        "(possibly filtered) — no more, no fewer."
                    ),
                    "missing": sorted(existing_ids - set(ids)),
                    "unexpected": sorted(set(ids) - existing_ids),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        model = queryset.model
        field_name = self.reorder_field
        with transaction.atomic():
            objs = []
            for position, obj_id in enumerate(ids):
                objs.append(model(pk=obj_id, **{field_name: position}))
            model.objects.bulk_update(objs, [field_name])

        return Response({"detail": "Order updated.", "order": ids}, status=status.HTTP_200_OK)
