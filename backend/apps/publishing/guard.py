"""Build guard (contract §5): refuse to build a snapshot that would gut the site."""
from . import registry
from .errors import CMSError
from .snapshot import validate

MAX_SHRINK = 0.30


class BuildGuardError(CMSError):
    def __init__(self, problems, shrinks):
        self.problems, self.shrinks = problems, shrinks
        only_shrink = shrinks and len(problems) == len(shrinks)
        super().__init__(
            "CMS_BUILD_GUARD",
            "Publish stopped before building: " + "; ".join(problems) + ".",
            fix=("If these removals are intended, publish again and confirm the shrink." if only_shrink
                 else "Fix the snapshot problems listed; nothing was built or uploaded."),
            side_effects="none",
        )


def check(snapshot, previous=None, confirm_shrink=False):
    """Raise BuildGuardError if the snapshot is invalid, misses a collection, or shrinks >30% unconfirmed."""
    problems, shrinks = [], []
    collections = snapshot.get("collections") if isinstance(snapshot, dict) else None
    missing = [name for name in registry.COLLECTIONS if not isinstance((collections or {}).get(name), list)]
    if missing:
        problems.append("missing collection(s) " + ", ".join(missing))
    errors = validate(snapshot)
    if errors and not missing:
        problems.append("schema: " + " | ".join(errors[:5]) + (f" (+{len(errors) - 5} more)" if len(errors) > 5 else ""))
    if previous and not confirm_shrink and collections:
        for name, prev_rows in sorted((previous.get("collections") or {}).items()):
            before, after = len(prev_rows or []), len((collections or {}).get(name) or [])
            if before and (before - after) / before > MAX_SHRINK:
                msg = f"{name} shrinks from {before} to {after} (-{round(100 * (before - after) / before)}%)"
                problems.append(msg)
                shrinks.append(msg)
    if problems:
        raise BuildGuardError(problems, shrinks)


check_snapshot = check  # name used by the qa lane's contract tests
