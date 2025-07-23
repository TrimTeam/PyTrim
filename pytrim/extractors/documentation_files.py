"""Documentation files dependency extractor."""

from pathlib import Path
from typing import Set

from ..utils.package_utils import normalize
from .base import BaseExtractor


class DocumentationFileExtractor(BaseExtractor):
    """Extractor for documentation files (.rst, .md)."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is a documentation file."""
        return file_path.suffix.lower() in (".rst", ".md")

    def extract(self, file_path: Path, seen: Set[Path] = None) -> Set[str]:
        """Extract dependencies from documentation files."""
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
            if "pip install" in s:
                parts = s.split("pip install")
                if len(parts) > 1:
                    pkg_part = parts[1].strip()
                    for pkg in pkg_part.split():
                        if not pkg.startswith("-") and pkg not in ["--", "&&", "||"]:
                            out.add(
                                normalize(
                                    pkg.split("==")[0].split(">=")[0].split("<=")[0]
                                )
                            )

        return out
