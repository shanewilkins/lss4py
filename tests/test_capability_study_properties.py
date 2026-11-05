"""Property tests for capability-study observed risk and nested evidence."""

import json
import math

import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from lss4py import CapabilityStudyResult, Specification, ValidationError, capability_study
from lss4py.domain import AnalyticalResult

MEASUREMENT = st.floats(
    min_value=-1e6,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
    allow_subnormal=False,
)
MEASUREMENTS = st.lists(
    MEASUREMENT,
    min_size=2,
    max_size=25,
)
LIMITS = st.tuples(
    st.floats(
        min_value=-1e5,
        max_value=1e5,
        allow_nan=False,
        allow_infinity=False,
        allow_subnormal=False,
    ),
    st.floats(
        min_value=1e-6,
        max_value=1e5,
        allow_nan=False,
        allow_infinity=False,
        allow_subnormal=False,
    ),
)


@settings(max_examples=60)
@given(short_values=MEASUREMENTS, long_values=st.one_of(st.none(), MEASUREMENTS), limits=LIMITS)
def test_capability_study_nested_and_observed_risk_invariants(short_values, long_values, limits):
    lsl, width = limits
    usl = lsl + width
    specification = Specification(
        "Generated CTQ",
        "units",
        "target",
        target=lsl + width / 2,
        lsl=lsl,
        usl=usl,
    )
    result = capability_study(
        pl.DataFrame({"value": short_values}),
        column="value",
        specification=specification,
        long_term_data=(None if long_values is None else pl.DataFrame({"value": long_values})),
        ci=False,
    )
    assert result.short_term_capability is not None
    assert result.short_term_distribution is not None
    assert result.short_term_capability.count == len(short_values)
    assert len(result.short_term_distribution.values) == len(short_values)
    assert_observed_risk(result.short_term_nonconformance, short_values, lsl, usl)
    if long_values is None:
        assert result.long_term_capability is None
        assert result.long_term_distribution is None
        assert result.long_term_nonconformance is None
    else:
        assert result.long_term_capability is not None
        assert result.long_term_distribution is not None
        assert result.long_term_capability.count == len(long_values)
        assert len(result.long_term_distribution.values) == len(long_values)
        assert result.long_term_nonconformance is not None
        assert_observed_risk(result.long_term_nonconformance, long_values, lsl, usl)


@settings(max_examples=40)
@given(short_values=MEASUREMENTS, long_values=st.one_of(st.none(), MEASUREMENTS), limits=LIMITS)
def test_capability_study_roundtrip_preserves_nested_results(short_values, long_values, limits):
    lsl, width = limits
    specification = Specification(
        "Generated CTQ",
        "units",
        "target",
        target=lsl + width / 2,
        lsl=lsl,
        usl=lsl + width,
    )
    result = capability_study(
        pl.DataFrame({"value": short_values}),
        column="value",
        specification=specification,
        long_term_data=(None if long_values is None else pl.DataFrame({"value": long_values})),
        ci=False,
    )
    restored = AnalyticalResult.from_dict(json.loads(result.to_json()))
    assert isinstance(restored, CapabilityStudyResult)
    assert restored.to_dict() == result.to_dict()


@settings(max_examples=30)
@given(
    before=st.lists(MEASUREMENT, min_size=1, max_size=10),
    after=st.lists(MEASUREMENT, max_size=10),
)
def test_capability_study_rejects_generated_missing_measurements(before, after):
    specification = Specification("Generated CTQ", "units", "target", target=0, lsl=-1, usl=1)
    with pytest.raises(ValidationError, match="missing measurements"):
        capability_study(
            pl.DataFrame({"value": [*before, None, *after]}),
            column="value",
            specification=specification,
            ci=False,
        )


def assert_observed_risk(summary, values, lsl, usl):
    below = sum(value < lsl for value in values)
    above = sum(value > usl for value in values)
    nonconforming = below + above
    assert summary["total"] == len(values)
    assert summary["below_lsl"] == below
    assert summary["above_usl"] == above
    assert summary["nonconforming"] == nonconforming
    assert math.isclose(
        summary["nonconforming_rate"],
        nonconforming / len(values),
        rel_tol=0,
        abs_tol=0,
    )
