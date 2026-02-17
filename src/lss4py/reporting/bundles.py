from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AnalysisBundle:
    title: str
    sections: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def to_markdown(bundle: AnalysisBundle) -> str:
    _ = bundle
    raise NotImplementedError("Markdown bundle rendering is not implemented yet.")
