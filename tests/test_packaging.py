"""pyproject.toml packaging metadata.

The repo is a flat layout with generated output/ and images/ folders, so
setuptools' auto-discovery fails ("Multiple top-level packages") unless the
module list is explicit. These tests pin the build configuration and keep the
declared version in step with VERSION in jig-plate.py.
"""
import importlib.util
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_declares_a_pep_621_capable_setuptools_build_backend():
    build = _PYPROJECT["build-system"]
    assert build["build-backend"] == "setuptools.build_meta"
    (req,) = [r for r in build["requires"] if r.startswith("setuptools")]
    minimum = int(req.split(">=")[1].split(".")[0])
    assert minimum >= 61  # first setuptools with [project] (PEP 621) support


def test_packages_only_the_library_module():
    assert _PYPROJECT["tool"]["setuptools"]["py-modules"] == ["jig_plate_base"]
    assert (_ROOT / "jig_plate_base.py").is_file()


def test_pyproject_version_matches_the_cli_version():
    spec = importlib.util.spec_from_file_location("jig_plate_cli_ver", _ROOT / "jig-plate.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    assert _PYPROJECT["project"]["version"] == cli.VERSION
