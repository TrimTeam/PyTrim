"""YAML files remover."""

import re
from pathlib import Path
from typing import List, Set

from ...utils.package_utils import normalize
from ..base import BaseRemover


class YamlRemover(BaseRemover):
    """Remover for YAML files (.yml, .yaml)."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is a YAML file."""
        return file_path.suffix.lower() in (".yml", ".yaml")

    def remove_unused(
        self, file_path: Path, unused: Set[str], lines: List[str]
    ) -> List[str]:
        """Remove unused dependencies from YAML files."""
        out = []

        for ln in lines:
            s = ln.strip()
            should_keep = True
            modified_line = ln

            if s.startswith("- "):
                # Check if this YAML list item contains conda commands
                if "conda install" in s or "conda create" in s:
                    # Remove unused packages from conda commands
                    original_line = ln
                    for pkg in unused:
                        # Remove package from conda command, handling various formats
                        # Match package as standalone word or with version specifiers
                        patterns = [
                            # pkg, pkg>=1.0, pkg==1.0, etc.
                            rf"\b{re.escape(pkg)}\b(?:[<>=!]+[^\s]*)?",
                            rf"\b{re.escape(pkg)}=[^\s]*",  # pkg=version
                        ]

                        for pattern in patterns:
                            # Use word boundaries and be careful not to remove parts of
                            # other package names
                            modified_line = re.sub(pattern, "", modified_line)

                    # Clean up extra spaces that may have been left behind
                    modified_line = re.sub(r"\s+", " ", modified_line)
                    modified_line = modified_line.strip()

                    # If the line was modified, use the modified version
                    if modified_line != original_line.strip():
                        # Preserve original indentation
                        indent = ln[: len(ln) - len(ln.lstrip())]
                        modified_line = indent + modified_line
                else:
                    # Regular YAML list item (not conda command)
                    pkg_with_extras = s[2:].split("=")[0].strip()
                    pkg_base = normalize(pkg_with_extras.split("[")[0].strip())
                    pkg_full = normalize(pkg_with_extras)

                    # Only check if this looks like a package name (not a command)
                    if not any(
                        cmd in pkg_base.lower()
                        for cmd in [
                            "python",
                            "source",
                            "flake8",
                            "coverage",
                            "coveralls",
                        ]
                    ):
                        if pkg_base in unused or pkg_full in unused:
                            should_keep = False

            if should_keep:
                out.append(modified_line)

        return out
