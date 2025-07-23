"""INI files remover with configparser logic."""

import configparser
from pathlib import Path
from typing import List, Set

from ...utils.package_utils import normalize
from ..base import BaseRemover


class IniFilesRemover(BaseRemover):
    """Remover for INI files (tox.ini) using configparser logic."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is an INI file."""
        return file_path.suffix.lower() == ".ini"

    def remove_unused(
        self, file_path: Path, unused: Set[str], lines: List[str]
    ) -> List[str]:
        """Remove unused dependencies from INI files using configparser."""
        # Use configparser to properly handle INI structure
        cp = configparser.ConfigParser()
        text = "\n".join(lines)

        try:
            cp.read_string(text)
            changes_made = False

            # Process each section that might contain dependencies
            for section_name, section in cp.items():
                if isinstance(section, configparser.SectionProxy):
                    for key, value in section.items():
                        if "deps" in key.lower() or "require" in key.lower():
                            # Process dependencies in this key
                            new_deps = []
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
                                    if pkg not in unused:
                                        new_deps.append(ln)
                                else:
                                    new_deps.append(ln)

                            # Update the section with filtered dependencies
                            if new_deps != value.splitlines():
                                cp.set(section_name, key, "\n".join(new_deps))
                                changes_made = True

            if changes_made:
                # Write back the modified INI content
                from io import StringIO

                output = StringIO()
                cp.write(output)
                result_lines = output.getvalue().splitlines()
                output.close()

                return result_lines
            else:
                return lines

        except Exception:
            # Fallback to line-by-line processing if configparser fails
            out = []
            for ln in lines:
                s = ln.strip()
                should_keep = True

                # Check if this line contains a package dependency
                for pkg in unused:
                    if pkg in s and not s.startswith("#") and not s.startswith("["):
                        should_keep = False
                        break

                if should_keep:
                    out.append(ln)

            return out
