# 0013: Backend parity testing

- Status: Proposed
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: TR-007, TR-017

## Context

ADR-0009 commits LSS4PY to backend-neutral APIs supporting pandas, Polars, and
PyArrow. However, without systematic testing, backend-specific bugs and numerical
drift will accumulate pre-1.0.

Additionally, TR-007 requires R SixSigma parity for retained capabilities. R
fixtures must be checked in and tested automatically against kernel functions.

## Decision

Implement two complementary test suites:

### 1. Parameterized Backend-Parity Tests

Use pytest parametrization to run every tabular calculation across backends:

```python
@pytest.fixture(params=["pandas", "polars"])
def backend(request):
    return request.param

@pytest.fixture
def sample_data(backend):
    pandas_df = pd.DataFrame({...})
    if backend == "pandas":
        return pandas_df
    elif backend == "polars":
        return pl.from_pandas(pandas_df)

def test_lead_time_parity(sample_data, backend):
    result_pd = lead_time(sample_data, ...)
    result_pl = lead_time(sample_data, ...)
    np.testing.assert_array_almost_equal(result_pd.values, result_pl.values)
    assert list(result_pd.keys) == list(result_pl.keys)
```

Every public tabular calculation must pass with pandas and Polars.

### 2. R SixSigma Parity Fixtures

Store versioned R fixtures in `tests/fixtures/r_parity/<family>/<name>/`:

```
tests/fixtures/r_parity/
  capability/
    normal_capability_v1/
      inputs.json         # Input data + parameters
      expected_outputs.json  # Expected Cp, Cpk, Z, etc.
      metadata.json       # R version, tolerance, notes
  spc/
    moving_range_v1/
      ...
```

Fixture format:

```json
{
  "inputs.json": {
    "data": [[1.5, 2.1, 1.9, 2.3], ...],
    "lsl": 1.0,
    "usl": 3.0
  },
  "expected_outputs.json": {
    "cp": 1.33,
    "cpk": 1.10,
    "z_score": 3.3
  },
  "metadata.json": {
    "r_package": "SixSigma",
    "r_version": "0.11.1",
    "scipy_version": "1.15.0",
    "tolerance": 1e-5,
    "notes": "Normal capability, two-sided spec"
  }
}
```

Automated test:

```python
@pytest.mark.parametrize("family,name", [
    ("capability", "normal_capability_v1"),
    ("spc", "moving_range_v1"),
])
def test_r_parity(family, name):
    inputs, expected, metadata = load_r_parity_fixture(family, name)
    result = capability_study(pd.DataFrame(inputs["data"]), ...)
    
    tolerance = metadata.get("tolerance", 1e-5)
    for key in expected:
        assert abs(result[key] - expected[key]) < tolerance
```

**Pragmatic tolerance:** Small numerical differences (e.g., ±1e-5) are acceptable
due to numerical stability and library updates (see ADR-0006).

## Alternatives considered

- **Smoke tests only.** Faster but misses drift. Rejected: backend parity is
  mandatory.
- **Separate test suites per backend.** Hard to maintain; drift. Rejected:
  parametrization is standard pytest.

## Consequences

- Every tabular calculation must define parameterized fixtures (pandas + Polars).
- R parity fixtures are part of the codebase; updated when kernels change.
- Backend-specific behavior must be documented as a known exception with
  justification and tests.
- Test matrix in CI grows; parallel test execution is recommended.
- PyArrow support is validated on a case-by-case basis; not all operations are
  supported.
