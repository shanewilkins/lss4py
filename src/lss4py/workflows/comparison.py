from lss4py.domain.models import ComparisonSlice


def compare_before_after(comparison: ComparisonSlice) -> dict[str, object]:
    _ = comparison
    raise NotImplementedError("Before/after comparison workflow is not implemented yet.")
