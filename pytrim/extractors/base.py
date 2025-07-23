"""Base extractor class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Set


class BaseExtractor(ABC):
    """Base class for dependency extractors."""

    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Check if this extractor can handle the given file."""
        pass

    @abstractmethod
    def extract(self, file_path: Path, seen: Set[Path] = None) -> Set[str]:
        """Extract dependencies from the file."""
        pass

    def read_file_safely(self, file_path: Path) -> str:
        """Safely read file content."""
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
