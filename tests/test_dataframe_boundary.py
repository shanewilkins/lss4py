"""Static enforcement for the private dataframe conversion boundary."""

import ast
from pathlib import Path


def test_narwhals_imports_remain_in_frame_boundary():
    """Prevent analytical execution from bypassing canonical Polars."""
    source_root = Path(__file__).parents[1] / "src" / "lss4py"
    allowed_boundary = Path("_frames.py")
    violations = []
    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports_narwhals = any(
                    alias.name == "narwhals" or alias.name.startswith("narwhals.")
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                imports_narwhals = bool(
                    node.module
                    and (node.module == "narwhals" or node.module.startswith("narwhals."))
                )
            else:
                imports_narwhals = False
            relative = path.relative_to(source_root)
            if imports_narwhals and relative != allowed_boundary:
                violations.append(relative.as_posix())
    assert violations == []
