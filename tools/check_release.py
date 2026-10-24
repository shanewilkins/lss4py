"""Validate source, tag and distribution identities before a release can publish."""

import argparse
import ast
import email
import tarfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_version() -> str:
    """Read the single version declaration without importing the source package."""
    tree = ast.parse((ROOT / "src/lss4py/_version.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets
        ):
            return str(ast.literal_eval(node.value))
    raise ValueError("Source version declaration is missing")


def check_metadata(raw: bytes, expected: str) -> None:
    """Require wheel/sdist metadata to identify exactly the selected source package."""
    metadata = email.message_from_bytes(raw)
    if metadata["Name"] != "lss4py" or metadata["Version"] != expected:
        raise ValueError("Distribution name/version differs from source")


def main() -> None:
    """Fail before upload for stale versions, missing artifacts or a mismatched release tag."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--tag")
    args = parser.parse_args()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    if source_version() != version:
        raise ValueError("Source version differs from pyproject.toml")
    if args.tag is not None and args.tag.removeprefix("v") != version:
        raise ValueError("Release tag differs from project version")
    wheels = list(args.dist.glob("*.whl"))
    sources = list(args.dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError("Release requires exactly one wheel and one source distribution")
    with zipfile.ZipFile(wheels[0]) as archive:
        [metadata] = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        check_metadata(archive.read(metadata), version)
    with tarfile.open(sources[0]) as archive:
        [metadata] = [m for m in archive.getmembers() if m.name.endswith("/PKG-INFO")]
        stream = archive.extractfile(metadata)
        if stream is None:
            raise ValueError("Source metadata is missing")
        check_metadata(stream.read(), version)
    print(f"Source, project, tag and both distribution versions agree: {version}")


if __name__ == "__main__":
    main()
