"""Main dependency extractor that coordinates all file type extractors."""

from pathlib import Path
from typing import List, Set

from .base import BaseExtractor
from .docker_files import DockerFileExtractor
from .documentation_files import DocumentationFileExtractor
from .ini_files import IniFileExtractor
from .python_files import PythonFileExtractor
from .requirements_files import RequirementsFileExtractor
from .shell_files import ShellFileExtractor
from .toml_files import TomlFileExtractor
from .yaml_files import YamlFileExtractor


class DependencyExtractor:
    """Main dependency extractor that coordinates all file type extractors."""

    def __init__(self):
        self.extractors: List[BaseExtractor] = [
            PythonFileExtractor(),
            RequirementsFileExtractor(),
            TomlFileExtractor(),
            YamlFileExtractor(),
            DocumentationFileExtractor(),
            ShellFileExtractor(),
            DockerFileExtractor(),
            IniFileExtractor(),
        ]

    def extract_deps(self, cfg: Path, seen: Set[Path] = None) -> Set[str]:
        """Extract dependencies from various config file formats."""
        if seen is None:
            seen = set()
        if cfg in seen:
            return set()

        # Find the appropriate extractor for this file
        for extractor in self.extractors:
            if extractor.can_handle(cfg):
                return extractor.extract(cfg, seen)

        # No extractor found for this file type
        return set()


# Create a default instance for backward compatibility
_default_extractor = DependencyExtractor()


def extract_deps(cfg: Path, seen: Set[Path] = None) -> Set[str]:
    """Extract dependencies from various config file formats.

    This is a convenience function that uses the default extractor instance.
    """
    return _default_extractor.extract_deps(cfg, seen)
