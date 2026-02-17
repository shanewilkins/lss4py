from pathlib import Path
from typing import Any


def load_tabular_records(path: str | Path) -> list[dict[str, Any]]:
    _ = path
    raise NotImplementedError("Tabular adapter is not implemented yet.")
