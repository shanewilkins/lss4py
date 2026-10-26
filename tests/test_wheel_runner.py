"""Regression contracts for testing the exact artifact selected for publication."""

import hashlib
import json
import sys

import pytest

from tools import check_wheel


def test_supplied_release_wheel_is_used_without_rebuilding(tmp_path, monkeypatch):
    wheel = tmp_path / "lss4py-0.2.0-py3-none-any.whl"
    wheel.write_bytes(b"release artifact")
    reports = tmp_path / "reports"
    commands = []
    monkeypatch.setattr(check_wheel, "run", lambda *args, **_kwargs: commands.append(args))
    monkeypatch.setenv("LSS4PY_E2E_ARTIFACTS", "")
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_wheel", "--wheel", str(wheel), "--ecosystem", "--artifacts-dir", str(reports)],
    )

    check_wheel.main()

    assert not any(command[:2] == ("uv", "build") for command in commands)
    installs = [command for command in commands if command[:3] == ("uv", "pip", "install")]
    assert len(installs) == 4
    assert all(command[-2].split("[")[0] == str(wheel) for command in installs)
    test_runs = [command for command in commands if command[1:4] == ("-I", "-m", "pytest")]
    junit = [arg for command in test_runs for arg in command if arg.startswith("--junitxml=")]
    assert {arg.rsplit("/", 1)[1] for arg in junit} == {
        "base.xml",
        "pandas.xml",
        "storage.xml",
        "ecosystem.xml",
    }
    assert json.loads((reports / "wheel.json").read_text()) == {
        "wheel": wheel.name,
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    }


@pytest.mark.parametrize("filename", ["missing.whl", "not-a-wheel.txt"])
def test_invalid_release_artifact_fails_before_any_build(tmp_path, monkeypatch, filename):
    path = tmp_path / filename
    if path.suffix != ".whl":
        path.write_text("not a wheel")
    monkeypatch.setattr(sys, "argv", ["check_wheel", "--wheel", str(path)])
    monkeypatch.setattr(
        check_wheel, "run", lambda *_args, **_kwargs: pytest.fail("unexpected command")
    )

    with pytest.raises(SystemExit) as error:
        check_wheel.main()

    assert error.value.code == 2


def test_wheel_changed_during_verification_is_rejected(tmp_path, monkeypatch):
    wheel = tmp_path / "lss4py-0.2.0-py3-none-any.whl"
    wheel.write_bytes(b"release artifact")
    monkeypatch.setattr(sys, "argv", ["check_wheel", "--wheel", str(wheel)])
    monkeypatch.delenv("LSS4PY_E2E_ARTIFACTS", raising=False)

    def run(*command, **_kwargs):
        if "--with-pandas" in command:
            wheel.write_bytes(b"changed artifact")

    monkeypatch.setattr(check_wheel, "run", run)

    with pytest.raises(ValueError, match="wheel changed"):
        check_wheel.main()
