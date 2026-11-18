"""Write-path check (CI, complements backend/.importlinter): content-app views write only via apps.publishing.

Rules, for apps/<content app>/views.py and apps/common/mixins.py:
  1. every class deriving from a DRF ModelViewSet / Create/Update/DestroyModelMixin also derives from
     CMSResourceMixin (create/update/destroy -> apps.publishing.content.*, with versions + audit);
  2. no direct ORM writes: .save( .delete( .create( .update( .bulk_create( .bulk_update(
     .get_or_create( .update_or_create( — mark a reviewed exception with `# write-path: ok <reason>`.
Exit 1 with file:line findings.  Usage: python tests/tools/write_paths.py [backend_dir]
"""
import ast
import sys
from pathlib import Path

CONTENT_APPS = ["core", "carousel", "team", "facilities", "services", "innovations", "products",
                "enterprises", "media_gallery", "common"]
WRITE_METHODS = {"save", "delete", "create", "update", "bulk_create", "bulk_update", "get_or_create",
                 "update_or_create"}
WRITABLE_BASES = {"ModelViewSet", "CreateModelMixin", "UpdateModelMixin", "DestroyModelMixin",
                  "CreateAPIView", "UpdateAPIView", "DestroyAPIView", "ListCreateAPIView",
                  "RetrieveUpdateAPIView", "RetrieveUpdateDestroyAPIView", "RetrieveDestroyAPIView"}


def _name(node):
    return node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", "")


def check_file(path):
    src = path.read_text()
    lines = src.splitlines()
    tree = ast.parse(src, str(path))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = {_name(b) for b in node.bases}
            if bases & WRITABLE_BASES and "CMSResourceMixin" not in bases:
                out.append(f"{path}:{node.lineno}: {node.name} is writable ({', '.join(sorted(bases & WRITABLE_BASES))}) "
                           "but does not use apps.publishing.drf.CMSResourceMixin")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in WRITE_METHODS:
            line = lines[node.lineno - 1]
            if "write-path: ok" in line:
                continue
            recv = ast.unparse(node.func.value)
            if recv in {"request.data", "self.request.data", "kwargs", "data", "headers"} or recv.endswith("_dict"):
                continue  # dict.update etc., not the ORM
            out.append(f"{path}:{node.lineno}: direct write `{recv}.{node.func.attr}(...)` — go through apps.publishing.content")
    return out


def main(backend):
    backend = Path(backend)
    files = [backend / "apps" / a / "views.py" for a in CONTENT_APPS] + [backend / "apps" / "common" / "mixins.py"]
    files = [f for f in files if f.exists()]
    findings = [f for path in files for f in check_file(path)]
    print("\n".join(findings) or f"write paths ok ({len(files)} files)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "backend"))
