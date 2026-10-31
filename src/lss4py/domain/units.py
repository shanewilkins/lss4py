"""Backend-neutral evidence for explicit duration preparation."""

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DurationConversion:
    """Converted native data and portable evidence, without Pint quantity objects."""

    _frame: Any
    _json: str

    def to_native(self) -> Any:
        """Return a native frame copy; Arrow tables are already immutable."""
        backend = self.to_dict()["backend"]
        if backend == "polars":
            return self._frame.clone()
        if backend == "pandas":
            return self._frame.copy(deep=True)
        return self._frame

    def to_dict(self) -> dict[str, Any]:
        """Return detached conversion evidence, excluding the table itself."""
        return json.loads(self._json)

    def to_json(self) -> str:
        """Serialize conversion declarations without registry-bound objects."""
        return self._json
