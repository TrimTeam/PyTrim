"""General config files remover (setup.py, setup.cfg, pyproject.toml, Pipfile etc)."""

import re
from pathlib import Path
from typing import List, Set

from ..base import BaseRemover
from ..line_utils import remove_package_from_line


class GeneralConfigRemover(BaseRemover):
    """Remover for general config files (setup.py, setup.cfg, pyproject.toml, Pipfile etc)."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is a general config file."""
        return (
            file_path.suffix.lower() in (".py", ".cfg", ".toml")
            or file_path.name == "Pipfile"
        )

    def remove_unused(
        self, file_path: Path, unused: Set[str], lines: List[str]
    ) -> List[str]:
        """Remove unused dependencies from general config files."""
        out = []
        i = 0

        while i < len(lines):
            ln = lines[i]
            should_skip_line = False
            modified_line = ln

            # Check if this is a TOML-style single package assignment line
            for pkg in unused:
                # Create variants of the package name (with hyphens and underscores)
                pkg_variants = {pkg, pkg.replace("-", "_"), pkg.replace("_", "-")}

                for pkg_variant in pkg_variants:
                    # Pattern for TOML assignment: package_name = "version" or
                    # package_name = {options}
                    # But avoid matching project metadata like version = "3.3.3" or name = "project"
                    toml_assignment_pattern = rf"^\s*{re.escape(pkg_variant)}\s*=\s*.*$"
                    if re.match(
                        toml_assignment_pattern, ln.strip(), re.IGNORECASE
                    ) and pkg_variant not in {
                        "version",
                        "name",
                        "description",
                        "authors",
                        "license",
                        "readme",
                        "homepage",
                        "repository",
                        "documentation",
                        "keywords",
                        "classifiers",
                        "requires-python",
                    }:
                        should_skip_line = True
                        break

                    # Also check for quoted variants in TOML
                    quoted_toml_patterns = [
                        rf'^\s*"{re.escape(pkg_variant)}"\s*=\s*.*$',
                        rf"^\s*'{re.escape(pkg_variant)}'\s*=\s*.*$",
                    ]
                    for pattern in quoted_toml_patterns:
                        if re.match(pattern, ln.strip(), re.IGNORECASE):
                            should_skip_line = True
                            break

                    # Check for single dependency lines in pyproject.toml like: "package" = "version"
                    # But be very specific to avoid removing lines with multiple dependencies
                    stripped_ln = ln.strip()
                    single_dep_patterns = [
                        # Match: "package" = "version" or "package" = {version = "1.0"}
                        rf'^\s*"{re.escape(pkg_variant)}"\s*=\s*.*$',
                        # Match: 'package' = 'version' or 'package' = {version = '1.0'}
                        rf"^\s*'{re.escape(pkg_variant)}'\s*=\s*.*$",
                    ]
                    for pattern in single_dep_patterns:
                        if re.match(pattern, stripped_ln, re.IGNORECASE):
                            should_skip_line = True
                            break

                if should_skip_line:
                    break

            if should_skip_line:
                i += 1
                continue  # Skip this entire line

            # Check if line contains any packages that need to be removed from
            # lists/multi-package lines
            has_unused = False
            for pkg in unused:
                # Create variants of the package name (with hyphens and underscores)
                pkg_variants = {pkg, pkg.replace("-", "_"), pkg.replace("_", "-")}

                for pkg_variant in pkg_variants:
                    ln_lower = ln.lower()
                    pkg_lower = pkg_variant.lower()
                    if pkg_lower in ln_lower and (
                        f'"{pkg_lower}"' in ln_lower
                        or f"'{pkg_lower}'" in ln_lower
                        or f" {pkg_lower}" in ln_lower
                        or f"{pkg_lower} " in ln_lower
                        or f"{pkg_lower}>" in ln_lower
                        or f"{pkg_lower}<" in ln_lower
                        or f"{pkg_lower}=" in ln_lower  # For package==version patterns
                        or f"{pkg_lower}[" in ln_lower
                        or f"]{pkg_lower}" in ln_lower
                        or f"{pkg_lower}," in ln_lower
                        or f",{pkg_lower}" in ln_lower
                    ):
                        has_unused = True
                        break

                if has_unused:
                    break

            if has_unused:
                # Check if we need to preserve trailing comma for multiline continuation
                preserve_comma = False
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Check if next line looks like a multiline continuation
                    if (
                        next_line
                        and lines[i + 1].startswith("  ")
                        and (
                            "=" not in next_line
                            or next_line.count("=") > next_line.count("==")
                        )
                        and (
                            '"' in next_line
                            or "'" in next_line
                            or any(char.isalpha() for char in next_line)
                        )
                    ):
                        preserve_comma = True

                # Remove individual packages from the line (for multi-package lines)
                original_modified = modified_line
                modified_line = remove_package_from_line(ln, unused, preserve_comma)

                # If the line was actually modified and it's now empty, skip it
                if modified_line.strip() == "" and original_modified.strip() != "":
                    i += 1
                    continue

            out.append(modified_line)
            i += 1

        return out
