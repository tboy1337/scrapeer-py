"""Tests for scrapeer._version module."""

import sys
from pathlib import Path
from unittest.mock import patch

from scrapeer._version import _fallback_version, _pyproject_path, get_version


class TestVersion:
    """Tests for version resolution."""

    def test_pyproject_path_exists(self) -> None:
        """Test that pyproject.toml is discoverable from the package."""
        assert _pyproject_path().is_file()

    def test_get_version_not_unknown(self) -> None:
        """Test that version resolves from pyproject.toml."""
        assert get_version() != "unknown"

    def test_fallback_version_matches_get_version(self) -> None:
        """Test fallback parser matches get_version output."""
        _fallback_version.cache_clear()
        assert _fallback_version() == get_version()

    def test_get_version_cached(self) -> None:
        """Test repeated get_version calls return the same value."""
        assert get_version() == get_version()

    def test_fallback_version_unknown_without_pyproject(self, tmp_path: Path) -> None:
        """Test fallback returns unknown when pyproject.toml is missing."""
        _fallback_version.cache_clear()
        missing = tmp_path / "missing.toml"
        with patch("scrapeer._version._pyproject_path", return_value=missing):
            assert _fallback_version() == "unknown"

    def test_fallback_version_unknown_without_version_key(self, tmp_path: Path) -> None:
        """Test fallback returns unknown when version key is absent."""
        _fallback_version.cache_clear()
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "scrapeer"\n', encoding="utf-8")
        with patch("scrapeer._version._pyproject_path", return_value=pyproject):
            assert _fallback_version() == "unknown"

    def test_pyproject_path_walk_up_fallback(self, tmp_path: Path) -> None:
        """Test fallback path when no pyproject.toml exists in ancestor directories."""
        isolated = tmp_path / "deep" / "nested"
        isolated.mkdir(parents=True)
        fake_module = isolated / "_version.py"
        fake_module.touch()
        with patch("scrapeer._version.__file__", str(fake_module)):
            result = _pyproject_path()
            assert result == isolated.parent.parent / "pyproject.toml"

    def test_pyproject_path_frozen_bundle(self, tmp_path: Path) -> None:
        """Test bundled pyproject path when running as a frozen executable."""
        bundled = tmp_path / "pyproject.toml"
        bundled.write_text('[project]\nversion = "9.9.9"\n', encoding="utf-8")
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
                assert _pyproject_path() == bundled

    def test_pyproject_path_frozen_without_bundle(self, tmp_path: Path) -> None:
        """Test fallback path when frozen but bundle metadata is missing."""
        empty_bundle = tmp_path / "bundle"
        empty_bundle.mkdir()
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", str(empty_bundle), create=True):
                expected = Path(__file__).resolve().parents[1] / "pyproject.toml"
                assert _pyproject_path() == expected

    def test_get_version_when_pyproject_has_no_version(self, tmp_path: Path) -> None:
        """Test metadata fallback when pyproject exists without a version field."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "scrapeer"\n', encoding="utf-8")
        _fallback_version.cache_clear()
        with patch("scrapeer._version._pyproject_path", return_value=pyproject):
            with patch(
                "scrapeer._version.version", return_value="2.0.0"
            ) as mock_version:
                assert get_version() == "2.0.0"
                mock_version.assert_called_once_with("scrapeer")

    def test_get_version_package_not_found(self, tmp_path: Path) -> None:
        """Test unknown version when package metadata and pyproject are missing."""
        from importlib.metadata import PackageNotFoundError

        missing = tmp_path / "missing.toml"
        _fallback_version.cache_clear()
        with patch("scrapeer._version._pyproject_path", return_value=missing):
            with patch(
                "scrapeer._version.version",
                side_effect=PackageNotFoundError("scrapeer"),
            ):
                assert get_version() == "unknown"
