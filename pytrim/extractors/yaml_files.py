"""YAML files dependency extractor."""

from pathlib import Path
from typing import Set

from ..utils.package_utils import normalize
from .base import BaseExtractor


class YamlFileExtractor(BaseExtractor):
    """Extractor for YAML files (.yml, .yaml)."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is a YAML file."""
        return file_path.suffix.lower() in (".yml", ".yaml")

    def extract(self, file_path: Path, seen: Set[Path] = None) -> Set[str]:
        """Extract dependencies from YAML files."""
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

        for ln in text.splitlines():
            s = ln.strip()
            if s.startswith("- "):
                # Check if this YAML list item contains conda commands
                if "conda install" in s or "conda create" in s:
                    out.update(self._extract_conda_packages(s))
                else:
                    # Regular YAML list item (not conda command)
                    pkg_with_extras = s[2:].split("=")[0].strip()
                    pkg_name = pkg_with_extras.split("[")[0].strip()
                    # Only add if it looks like a package name (not a command)
                    if (
                        not any(
                            cmd in pkg_name.lower()
                            for cmd in [
                                "python",
                                "source",
                                "flake8",
                                "coverage",
                                "coveralls",
                            ]
                        )
                        and pkg_name
                    ):
                        out.add(normalize(pkg_name))
                        if "[" in pkg_with_extras and "]" in pkg_with_extras:
                            out.add(normalize(pkg_with_extras))

        return out

    def _extract_conda_packages(self, line: str) -> Set[str]:
        """Extract packages from conda commands."""
        out = set()
        parts = line.split()
        skip_next = False

        for i, part in enumerate(parts):
            if skip_next:
                skip_next = False
                continue

            # Skip command and common flags
            if part in [
                "conda",
                "install",
                "create",
                "-q",
                "-y",
                "--yes",
                "--quiet",
                "-",
            ]:
                continue
            elif part.startswith("-"):
                # Skip flags, some may have values
                if part in ["-n", "-c", "--name", "--channel", "--prefix", "-p"]:
                    skip_next = True  # Skip the next argument (flag value)
                continue
            elif "=" in part and not part.startswith("-"):
                # This could be python=3.8 or $VAR=value, extract package name
                pkg_name = part.split("=")[0].strip()
                if pkg_name and not pkg_name.startswith("$") and pkg_name != "python":
                    out.add(normalize(pkg_name))
            elif part and not part.startswith("$") and not part.startswith("-"):
                # Regular package name
                # Split on common version specifiers
                pkg_clean = (
                    part.split("==")[0]
                    .split(">=")[0]
                    .split("<=")[0]
                    .split(">")[0]
                    .split("<")[0]
                )
                if pkg_clean and pkg_clean not in ["python"]:
                    out.add(normalize(pkg_clean))

        return out
