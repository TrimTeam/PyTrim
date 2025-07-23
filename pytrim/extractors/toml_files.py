"""TOML files dependency extractor."""

from pathlib import Path
from typing import Set

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from ..utils.package_utils import normalize
from .base import BaseExtractor


class TomlFileExtractor(BaseExtractor):
    """Extractor for TOML files (pyproject.toml, Pipfile)."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is a TOML file we can handle."""
        return (
            file_path.suffix.lower() == ".toml"
            or file_path.name == "Pipfile"
        )

    def extract(self, file_path: Path, seen: Set[Path] = None) -> Set[str]:
        """Extract dependencies from TOML files."""
        if seen is None:
            seen = set()
        if file_path in seen:
            return set()
        seen.add(file_path)

        if not file_path.is_file():
            return set()

        text = self.read_file_safely(file_path)
        if not text:
            return set()

        out = set()

        # Handle Pipfile
        if file_path.name == "Pipfile":
            out.update(self._extract_pipfile(text))


        # Handle pyproject.toml
        elif file_path.suffix == ".toml":
            out.update(self._extract_pyproject_toml(text))

        return out

    def _extract_pipfile(self, text: str) -> Set[str]:
        """Extract from Pipfile."""
        out = set()
        try:
            data = tomllib.loads(text)
            for section in ["packages", "dev-packages"]:
                if section in data:
                    for pkg in data[section]:
                        out.add(normalize(pkg))
        except Exception:
            pass
        return out


    def _extract_pyproject_toml(self, text: str) -> Set[str]:
        """Extract from pyproject.toml."""
        out = set()
        try:
            data = tomllib.loads(text)

            # PEP 621 format
            proj = data.get("project", {})
            for d in proj.get("dependencies", []):
                pkg_with_extras = (
                    d.split("==")[0]
                    .split(">=")[0]
                    .split("<=")[0]
                    .split(">")[0]
                    .split("<")[0]
                    .split("!")[0]
                    .split("~=")[0]
                    .split(";")[0]
                    .strip()
                )
                pkg_name = pkg_with_extras.split("[")[0].strip()
                if pkg_name:
                    out.add(normalize(pkg_name))
                    # Also add the package with extras
                    if "[" in pkg_with_extras and "]" in pkg_with_extras:
                        out.add(normalize(pkg_with_extras))

            for lst in proj.get("optional-dependencies", {}).values():
                for d in lst:
                    pkg_with_extras = (
                        d.split("==")[0]
                        .split(">=")[0]
                        .split("<=")[0]
                        .split(">")[0]
                        .split("<")[0]
                        .split("!")[0]
                        .split("~=")[0]
                        .split(";")[0]
                        .strip()
                    )
                    pkg_name = pkg_with_extras.split("[")[0].strip()
                    if pkg_name:
                        out.add(normalize(pkg_name))
                        # Also add the package with extras
                        if "[" in pkg_with_extras and "]" in pkg_with_extras:
                            out.add(normalize(pkg_with_extras))

            # Poetry format
            poetry = data.get("tool", {}).get("poetry", {})
            deps = poetry.get("dependencies", {})
            for pkg_name, pkg_spec in deps.items():
                if pkg_name != "python":
                    out.add(normalize(pkg_name))
                    # Handle extras in poetry format: httpx = {version = "^0.24.1", extras = ["http2"]}
                    if isinstance(pkg_spec, dict) and "extras" in pkg_spec:
                        for extra in pkg_spec["extras"]:
                            out.add(normalize(f"{pkg_name}[{extra}]"))

            for d in poetry.get("dev-dependencies", {}):
                out.add(normalize(d))
            for lst in poetry.get("extras", {}).values():
                for d in lst:
                    out.add(normalize(d))
        except Exception:
            pass
        return out
