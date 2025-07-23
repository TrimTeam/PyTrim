"""Base classes for config file removers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Set


class BaseRemover(ABC):
    """Base class for config file removers."""

    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Check if this remover can handle the given file."""
        pass

    @abstractmethod
    def remove_unused(
        self, file_path: Path, unused: Set[str], lines: List[str]
    ) -> List[str] | None:
        """Remove unused dependencies from file lines."""
        pass

    def read_file_safely(self, file_path: Path) -> str:
        """Safely read file content."""
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
