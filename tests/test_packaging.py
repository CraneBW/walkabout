"""Tests for packaging and PyPI publishing configuration."""
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Optional

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ── Helpers ──────────────────────────────────────────────────────────────


def _which(cmd: str) -> Optional[str]:
    """Return path to *cmd* executable, or None."""
    import shutil
    return shutil.which(cmd)


def _load_pyproject() -> dict:
    """Parse pyproject.toml and return the dict."""
    import tomli

    path = PROJECT_ROOT / "pyproject.toml"
    with open(path, "rb") as f:
        return tomli.load(f)


# ── pyproject.toml structure ────────────────────────────────────────────


class TestPyprojectToml:
    """Tests that pyproject.toml is complete and valid for PyPI publishing."""

    def test_is_valid_toml(self):
        """pyproject.toml must be parseable as TOML."""
        data = _load_pyproject()
        assert isinstance(data, dict)

    def test_has_name(self):
        data = _load_pyproject()
        assert "project" in data
        name = data["project"].get("name")
        assert name == "walkabout"

    def test_has_version(self):
        data = _load_pyproject()
        version = data["project"].get("version")
        assert version is not None
        assert isinstance(version, str)

    def test_has_description(self):
        data = _load_pyproject()
        desc = data["project"].get("description")
        assert desc is not None
        assert isinstance(desc, str)

    def test_has_readme(self):
        """Must declare a README for PyPI."""
        data = _load_pyproject()
        readme = data["project"].get("readme")
        assert readme is not None, "pyproject.toml is missing `readme` field"

    def test_has_license(self):
        """Must declare a license."""
        data = _load_pyproject()
        license_info = data["project"].get("license")
        assert license_info is not None, "pyproject.toml is missing [project.license]"

    def test_has_classifiers(self):
        """Must have at least one Trove classifier (typically License,
        Python version, etc.)."""
        data = _load_pyproject()
        classifiers = data["project"].get("classifiers", [])
        assert len(classifiers) > 0, "pyproject.toml has no classifiers"

    def test_has_urls(self):
        """Must declare Homepage, Repository, and Issues URLs."""
        data = _load_pyproject()
        urls = data["project"].get("urls", {})
        assert "Homepage" in urls, "Missing urls.Homepage"
        assert "Repository" in urls, "Missing urls.Repository"
        assert "Issues" in urls, "Missing urls.Issues"

    def test_has_scripts_entry_point(self):
        """`walkabout` CLI entry point must exist."""
        data = _load_pyproject()
        scripts = data["project"].get("scripts", {})
        entry = scripts.get("walkabout")
        assert entry == "walkabout.__main__:main", (
            f"Expected 'walkabout.__main__:main', got {entry!r}"
        )

    def test_has_build_system(self):
        """[build-system] must declare hatchling."""
        data = _load_pyproject()
        bs = data.get("build-system", {})
        assert bs.get("build-backend") == "hatchling.build"
        assert "hatchling" in bs.get("requires", [])


# ── Version consistency ─────────────────────────────────────────────────


class TestVersionConsistency:
    """Version in __init__.py must match pyproject.toml."""

    def test_version_matches(self):
        data = _load_pyproject()
        pyproject_version = data["project"]["version"]

        # Import version from the package
        sys.path.insert(0, str(PROJECT_ROOT))
        import walkabout

        pkg_version = walkabout.__version__
        assert pkg_version == pyproject_version, (
            f"walkabout.__version__ ({pkg_version!r}) != "
            f"pyproject.toml version ({pyproject_version!r})"
        )


# ── Build ───────────────────────────────────────────────────────────────


class TestBuild:
    """Package must build successfully and produce correct artifacts."""

    @pytest.mark.skipif(
        not _which("python"),
        reason="python not on PATH",
    )
    def test_build_sdist_and_wheel(self, tmp_path):
        """`python -m build` must produce .tar.gz and .whl artifacts."""
        result = subprocess.run(
            [sys.executable, "-m", "build", "--outdir", str(tmp_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"build failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

        artifacts = list(tmp_path.iterdir())
        wheels = [a for a in artifacts if a.suffix == ".whl"]
        sdists = [a for a in artifacts if a.name.endswith(".tar.gz")]

        assert len(wheels) >= 1, f"No wheel found in {tmp_path}"
        assert len(sdists) >= 1, f"No sdist found in {tmp_path}"

    def test_wheel_includes_frontend(self, tmp_path):
        """The wheel must contain frontend/dist/index.html."""
        result = subprocess.run(
            [sys.executable, "-m", "build", "--outdir", str(tmp_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"build failed:\n{result.stderr}"

        wheels = sorted(tmp_path.glob("*.whl"))
        assert wheels, "No wheel produced by build"

        wheel_path = wheels[-1]
        with zipfile.ZipFile(wheel_path) as zf:
            names = zf.namelist()

        # frontend/dist must be included
        frontend_files = [n for n in names if "frontend/dist" in n]
        assert len(frontend_files) > 0, (
            f"No frontend/dist files found in wheel. "
            f"Wheel contents: {names}"
        )
        assert any("index.html" in n for n in frontend_files), (
            "frontend/dist/index.html not found in wheel"
        )


# ── CLI entry point ─────────────────────────────────────────────────────


class TestCliEntryPoint:
    """The installed walkabout CLI entry point must be invocable."""

    @pytest.mark.skipif(
        not _which("walkabout"),
        reason="walkabout not on PATH (package not installed)",
    )
    def test_cli_help(self):
        """`walkabout --help` should print usage and exit 0."""
        result = subprocess.run(
            ["walkabout", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Walkabout" in result.stdout or "walkabout" in result.stdout.lower()


# ── MANIFEST.in ─────────────────────────────────────────────────────────


class TestManifestIn:
    """MANIFEST.in controls what goes into the sdist."""

    def test_manifest_in_exists(self):
        manifest = PROJECT_ROOT / "MANIFEST.in"
        assert manifest.exists(), "MANIFEST.in is missing"

    def test_manifest_includes_frontend(self):
        manifest = PROJECT_ROOT / "MANIFEST.in"
        text = manifest.read_text()
        assert "frontend/dist" in text or "recursive-include" in text, (
            "MANIFEST.in should include frontend/dist"
        )

    def test_manifest_excludes_tests(self):
        manifest = PROJECT_ROOT / "MANIFEST.in"
        text = manifest.read_text()
        lines = [line for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
        exclude_lines = [line for line in lines if "exclude" in line.lower() or "prune" in line.lower()]
        has_test_exclude = any("test" in line.lower() for line in exclude_lines)
        assert has_test_exclude, "MANIFEST.in should exclude tests/"


# ── CI workflow ─────────────────────────────────────────────────────────


class TestPublishWorkflow:
    """The publish CI workflow config must exist and be valid YAML."""

    def test_publish_workflow_exists(self):
        workflow = PROJECT_ROOT / ".github" / "workflows" / "publish.yml"
        assert workflow.exists(), ".github/workflows/publish.yml is missing"

    def test_publish_workflow_triggers_on_version_tags(self):
        workflow = PROJECT_ROOT / ".github" / "workflows" / "publish.yml"
        text = workflow.read_text()
        assert "v*" in text, "Workflow should trigger on v* tags"


