"""Explicit bindings and semantics for prepared numeric order measurements."""

from dataclasses import asdict, dataclass
from math import isfinite

from lss4py.errors import ValidationError


@dataclass(frozen=True, slots=True)
class OrderSummaryContract:
    """Declare prepared cases, shared numeric clock, boundary and VA convention.

    Case IDs are nonmissing unique strings. All time columns share the declared
    unit/clock; no calendar parsing or unit conversion is performed. Optional
    processing/wait/setup columns must be supplied together. Comparisons allow
    only the declared absolute rounding tolerance, never a relative tolerance.
    """

    case_id_column: str
    arrival_column: str
    readiness_column: str
    lead_time_column: str
    value_add_time_column: str
    unit: str
    clock: str
    boundary: str
    cohort: str
    value_add_convention: str
    processing_time_column: str | None = None
    wait_time_column: str | None = None
    setup_time_column: str | None = None
    tolerance: float = 1e-8

    def __post_init__(self) -> None:
        """Reject incomplete or ambiguous declarations before looking at observations."""
        required = (
            self.case_id_column,
            self.arrival_column,
            self.readiness_column,
            self.lead_time_column,
            self.value_add_time_column,
            self.clock,
            self.boundary,
            self.cohort,
            self.value_add_convention,
        )
        _validate_components(
            (self.processing_time_column, self.wait_time_column, self.setup_time_column)
        )
        _validate_bindings(required, self.time_columns + (self.case_id_column,))
        _validate_units_and_tolerance(self.unit, self.tolerance)

    @property
    def time_columns(self) -> tuple[str, ...]:
        """Return the explicitly bound numeric fields without optional absent columns."""
        required = (
            self.arrival_column,
            self.readiness_column,
            self.lead_time_column,
            self.value_add_time_column,
        )
        return required + tuple(
            c
            for c in (self.processing_time_column, self.wait_time_column, self.setup_time_column)
            if c is not None
        )

    def to_dict(self) -> dict:
        """Serialize every declaration and tolerance for reproducible evidence."""
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> OrderSummaryContract:
        """Restore a declaration, rejecting unknown or incomplete fields."""
        try:
            return cls(**value)
        except TypeError as exc:
            raise ValidationError("Invalid order summary contract fields.") from exc


def _validate_bindings(required: tuple, names: tuple) -> None:
    """Require explicit text declarations and distinct field roles."""
    if any(not isinstance(v, str) or not v.strip() for v in required):
        raise ValidationError("Order summary bindings and semantic declarations must be nonblank.")
    if len(set(names)) != len(names):
        raise ValidationError("Order summary column bindings must be distinct.")


def _validate_components(components: tuple) -> None:
    """Keep the processing/wait/setup partition declaration complete or absent."""
    if any(c is not None for c in components) and not all(
        isinstance(c, str) and c.strip() for c in components
    ):
        raise ValidationError("Processing, waiting, and setup bindings must be supplied together.")


def _validate_units_and_tolerance(unit: str, tolerance: float) -> None:
    """Validate measurement units and a finite absolute comparison tolerance."""
    if unit not in ("seconds", "minutes", "hours", "days"):
        raise ValidationError("Order summary unit must be seconds, minutes, hours, or days.")
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        raise ValidationError("Order summary tolerance must be a finite nonnegative number.")
    try:
        valid = isfinite(tolerance) and tolerance >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValidationError("Order summary tolerance must be a finite nonnegative number.")
