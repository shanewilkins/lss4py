"""Explicit policy for reconstructing orders from numeric activity endpoints."""

from dataclasses import asdict, dataclass
from math import isfinite

from lss4py.errors import ValidationError


@dataclass(frozen=True)
class OrderReconstructionPolicy:
    """Declare a serial order path with selected parallel activity/pass envelopes.

    Parallel envelopes use minimum queue/setup and maximum work start/end.
    This is a declared accounting convention, not a general branch algorithm.
    All other activity/pass groups must contain exactly one source record.
    """

    arrival_activity: str
    readiness_activity: str
    required_activities: tuple[str, ...]
    parallel_activities: tuple[str, ...]
    value_add_activities: tuple[str, ...]
    rework_column: str
    rework_value: str
    non_rework_value: str
    correction_activity: str
    cohort: str
    value_add_convention: str
    required_non_value_add_activities: tuple[str, ...] = ()
    parallel_load_count_column: str | None = None
    tolerance: float = 1e-8

    def __post_init__(self) -> None:
        """Freeze activity sets and reject ambiguous or incomplete declarations."""
        self._freeze_activities()
        names = (
            "arrival_activity",
            "readiness_activity",
            "rework_column",
            "rework_value",
            "non_rework_value",
            "correction_activity",
            "cohort",
            "value_add_convention",
        )
        for name in names:
            _require_text(getattr(self, name))
        if self.parallel_load_count_column is not None:
            _require_text(self.parallel_load_count_column)
        self._check_consistency()

    def _freeze_activities(self) -> None:
        """Normalize explicit activity sets without accepting a string as a sequence."""
        for name in (
            "required_activities",
            "parallel_activities",
            "value_add_activities",
            "required_non_value_add_activities",
        ):
            raw = getattr(self, name)
            if not isinstance(raw, (list, tuple)):
                raise ValidationError(f"{name} must be a sequence of activity names.")
            for value in raw:
                _require_text(value)
            values = tuple(raw)
            if len(set(values)) != len(values):
                raise ValidationError(f"{name} must contain distinct activity names.")
            object.__setattr__(self, name, values)

    def _check_consistency(self) -> None:
        """Reject conflicting boundary, correction and tolerance declarations."""
        if self.rework_value == self.non_rework_value:
            raise ValidationError("Rework and non-rework values must differ.")
        if self.arrival_activity == self.readiness_activity:
            raise ValidationError("Arrival and readiness activities must differ.")
        if set(self.value_add_activities) & set(self.required_non_value_add_activities):
            raise ValidationError("VA and RNVA activity sets must be disjoint.")
        if self.correction_activity in self.value_add_activities:
            raise ValidationError("Corrections cannot be value added.")
        if self.correction_activity in self.parallel_activities:
            raise ValidationError("Correction occurrences must be singular activity/pass records.")
        if isinstance(self.tolerance, bool) or not isinstance(self.tolerance, (int, float)):
            raise ValidationError("tolerance must be numeric.")
        if not isfinite(self.tolerance) or self.tolerance < 0:
            raise ValidationError("tolerance must be finite and nonnegative.")

    def to_dict(self) -> dict:
        """Return the full declared accounting convention for provenance."""
        return asdict(self)


def _require_text(value: str) -> None:
    """Require meaningful declarations without guessing from values or column names."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Policy declarations must be nonblank strings.")
