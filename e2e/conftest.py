"""Fixtures for customer workflows executed only from a wheel installation."""

import json
import sys
from importlib import metadata
from pathlib import Path

import polars as pl
import pytest

import lss4py


def pytest_addoption(parser):
    """Enable the required pandas matrix after installing the optional extra."""
    parser.addoption("--with-pandas", action="store_true")
    parser.addoption("--ecosystem", action="store_true")


def pytest_ignore_collect(collection_path, config):
    """Collect ecosystem tests only in the explicitly installed optional environment."""
    return collection_path.name == "ecosystem" and not config.getoption("--ecosystem")


def pytest_generate_tests(metafunc):
    """Run tabular studies on each explicitly installed backend without skips."""
    if "backend" in metafunc.fixturenames:
        backends = (
            ["polars", "pandas"] if metafunc.config.getoption("--with-pandas") else ["polars"]
        )
        metafunc.parametrize("backend", backends)


@pytest.fixture(scope="session", autouse=True)
def installed_package(request):
    """Reject source imports, editable installs and leaked development dependencies."""
    package = Path(lss4py.__file__).resolve()
    assert package.is_relative_to(Path(sys.prefix).resolve()), package
    distribution = metadata.distribution("lss4py")
    assert distribution.version == lss4py.__version__
    direct_url = json.loads(distribution.read_text("direct_url.json") or "{}")
    assert not direct_url.get("dir_info", {}).get("editable", False)
    assert direct_url["url"].endswith(".whl")
    assert "archive_info" in direct_url
    with pytest.raises(metadata.PackageNotFoundError):
        metadata.version("pytest-cov")
    if not request.config.getoption("--ecosystem"):
        for package in ("flo-lang", "matplotlib", "seaborn"):
            with pytest.raises(metadata.PackageNotFoundError):
                metadata.version(package)


@pytest.fixture
def fixtures():
    """Locate the copied CSV and JSON study inputs."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def expected(fixtures):
    """Load fixed independently calculated expectations."""
    return json.loads((fixtures / "expected.json").read_text())


@pytest.fixture
def read_csv(backend):
    """Use the backend's CSV reader as an analyst would, preserving case identifiers."""
    if backend == "polars":
        return lambda path: pl.read_csv(path, schema_overrides={"case": pl.String})
    import pandas as pd

    return lambda path: pd.read_csv(path, dtype={"case": str})


@pytest.fixture
def export_json(tmp_path):
    """Write, reopen and strictly parse exported results, including public to_json output."""

    def export(name, results):
        payload = {key: json.loads(value.to_json()) for key, value in results.items()}
        destination = tmp_path / f"{name}.json"
        destination.write_text(json.dumps(payload, allow_nan=False, indent=2))
        return json.loads(destination.read_text())

    return export
