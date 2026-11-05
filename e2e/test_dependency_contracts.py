"""Core dependency contracts exercised from an isolated wheel installation."""

import os
import subprocess
import sys
from importlib import metadata

import polars as pl
from packaging.requirements import Requirement


def test_base_install_declares_bounded_pandera_polars_dependency():
    """Keep Pandera core-only except for its Polars validation backend."""
    requirements = {
        requirement.name: requirement
        for value in metadata.requires("lss4py") or ()
        if (requirement := Requirement(value)).marker is None
    }
    pandera = requirements["pandera"]
    assert pandera.extras == {"polars"}
    assert str(pandera.specifier) == "<0.36,>=0.35"


def test_pandera_validates_locked_polars_without_coercion():
    """Prove the selected Pandera floor supports the locked Polars runtime."""
    import pandera.polars as pa

    frame = pl.DataFrame({"value": [1.0, 2.0]})
    schema = pa.DataFrameSchema(
        {"value": pa.Column(float, nullable=False)},
        strict=True,
        coerce=False,
    )
    validated = schema.validate(frame)
    assert validated.equals(frame)
    assert validated.schema == frame.schema


def test_import_does_not_enable_pandera_narwhals_backend():
    """LSS4PY must not mutate Pandera's process-global backend selection."""
    environment = os.environ.copy()
    environment.pop("PANDERA_USE_NARWHALS_BACKEND", None)
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import pandera.config as config; "
                "assert config.CONFIG.use_narwhals_backend is False; "
                "before = config.CONFIG; "
                "import lss4py; "
                "assert config.CONFIG == before; "
                "assert config.CONFIG.use_narwhals_backend is False"
            ),
        ],
        env=environment,
        check=True,
    )


def test_import_does_not_load_pandera_backends():
    """Optional dataframe packages must not make validation an import side effect."""
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import sys; "
                "import lss4py; "
                "assert not any(name == 'pandera' or name.startswith('pandera.') "
                "for name in sys.modules)"
            ),
        ],
        check=True,
    )
