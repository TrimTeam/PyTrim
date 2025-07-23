"""Requirements files dependency extractor."""

from pathlib import Path
from typing import Set

from ..utils.package_utils import normalize
from .base import BaseExtractor


class RequirementsFileExtractor(BaseExtractor):
    """Extractor for requirements files (.txt, .in)."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is a requirements file."""
        return file_path.suffix.lower() in (".txt", ".in")

    def extract(self, file_path: Path, seen: Set[Path] = None) -> Set[str]:
        """Extract dependencies from requirements files."""
        if seen is None:
            seen = set()
        if file_path in seen:
            return set()
        seen.add(file_path)

        # Handle special case of directories with requires.txt
        if file_path.is_dir() and file_path.name.endswith(".egg-info"):
            req_file = file_path / "requires.txt"
            if req_file.exists():
                return self.extract(req_file, seen)
            return set()

        if not file_path.is_file():
            return set()

        text = self.read_file_safely(file_path)
        if not text:
            return set()

        out = set()

        for ln in text.splitlines():
            s = ln.strip()
            if not s or s.startswith("#") or s.lstrip().startswith("--hash="):
                continue
            if s.startswith("-r"):
                ref = file_path.parent / s.split(maxsplit=1)[1]
                out |= self.extract(ref, seen)
            else:
                # Parse package names with extras like pandas[excel]
                # More comprehensive parsing to handle all edge cases
                pkg_with_extras = (
                    s.split("==")[0]
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
                if pkg_name:  # Only add non-empty package names
                    out.add(normalize(pkg_name))
                    # Also add the package with extras
                    if "[" in pkg_with_extras and "]" in pkg_with_extras:
                        out.add(normalize(pkg_with_extras))

        return out
