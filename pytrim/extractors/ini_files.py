"""INI files dependency extractor."""

import configparser
from pathlib import Path
from typing import Set

from ..utils.package_utils import normalize
from .base import BaseExtractor


class IniFileExtractor(BaseExtractor):
    """Extractor for INI files (setup.cfg, tox.ini)."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is an INI file."""
        return file_path.suffix.lower() in (".cfg", ".ini")

    def extract(self, file_path: Path, seen: Set[Path] = None) -> Set[str]:
        """Extract dependencies from INI files."""
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

        if file_path.suffix == ".cfg":
            out.update(self._extract_setup_cfg(text))
        elif file_path.suffix == ".ini":
            out.update(self._extract_tox_ini(text))

        return out

    def _extract_setup_cfg(self, text: str) -> Set[str]:
        """Extract from setup.cfg files."""
        out = set()
        cp = configparser.ConfigParser()
        try:
            cp.read_string(text)
            if "options" in cp and "install_requires" in cp["options"]:
                for ln in cp["options"]["install_requires"].splitlines():
                    s = ln.strip()
                    if s and not s.startswith("#"):
                        pkg = normalize(
                            s.split("==")[0]
                            .split(">=")[0]
                            .split("<=")[0]
                            .split(">")[0]
                            .split("<")[0]
                            .split("!")[0]
                            .split("~=")[0]
                            .split(";")[0]
                        )
                        out.add(pkg)
            if "options.extras_require" in cp:
                for extras in cp["options.extras_require"].values():
                    for ln in extras.splitlines():
                        s = ln.strip()
                        if s and not s.startswith("#"):
                            pkg = normalize(
                                s.split("==")[0]
                                .split(">=")[0]
                                .split("<=")[0]
                                .split(">")[0]
                                .split("<")[0]
                                .split("!")[0]
                                .split("~=")[0]
                                .split(";")[0]
                            )
                            out.add(pkg)
        except Exception:
            pass
        return out

    def _extract_tox_ini(self, text: str) -> Set[str]:
        """Extract from tox.ini files."""
        out = set()
        cp = configparser.ConfigParser()
        try:
            cp.read_string(text)
            for section_name, section in cp.items():
                if isinstance(section, configparser.SectionProxy):
                    for key, value in section.items():
                        if "deps" in key.lower() or "require" in key.lower():
                            for ln in value.splitlines():
                                s = ln.strip()
                                if s and not s.startswith("#"):
                                    pkg = normalize(
                                        s.split("==")[0]
                                        .split(">=")[0]
                                        .split("<=")[0]
                                        .split(">")[0]
                                        .split("<")[0]
                                        .split("!")[0]
                                        .split("~=")[0]
                                        .split(";")[0]
                                    )
                                    out.add(pkg)
        except Exception:
            pass
        return out
