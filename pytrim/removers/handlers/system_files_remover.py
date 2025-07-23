"""System files remover (shell scripts, documentation, Docker files)."""

import re
from pathlib import Path
from typing import List, Set

from ..base import BaseRemover


class SystemFilesRemover(BaseRemover):
    """Remover for system files (shell scripts, documentation, Docker files)."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is a system file we can handle."""
        return file_path.suffix.lower() in (
            ".rst",
            ".md",
            ".sh",
            ".dockerfile",
        ) or file_path.name.lower().startswith("dockerfile")

    def remove_unused(
        self, file_path: Path, unused: Set[str], lines: List[str]
    ) -> List[str]:
        """Remove unused dependencies from system files."""
        out = []

        for ln in lines:
            modified_line = ln
            original_line = ln

            # Handle conda commands in shell scripts and documentation
            if ("conda install" in ln or "conda create" in ln) and unused:
                for pkg in unused:
                    # Remove package from conda command, handling various formats
                    patterns = [
                        # pkg, pkg>=1.0, pkg==1.0, etc.
                        rf"\b{re.escape(pkg)}\b(?:[<>=!]+[^\s]*)?",
                        rf"\b{re.escape(pkg)}=[^\s]*",  # pkg=version
                    ]

                    for pattern in patterns:
                        modified_line = re.sub(pattern, "", modified_line)

                # Clean up extra spaces
                modified_line = re.sub(r"\s+", " ", modified_line)
                # Preserve original indentation
                indent = original_line[
                    : len(original_line) - len(original_line.lstrip())
                ]
                modified_line = indent + modified_line.strip()

                out.append(modified_line)
            elif (
                any(
                    pkg_mgr in ln
                    for pkg_mgr in [
                        "pip install",
                        "apt-get install",
                        "apt install",
                        "yum install",
                        "dnf install",
                        "pacman -S",
                        "brew install",
                    ]
                )
                and unused
            ):
                # Handle package manager commands in shell scripts and documentation
                for pkg in unused:
                    patterns = []

                    if "pip install" in ln:
                        # For pip install, handle Python package specifications
                        patterns.append(
                            rf"\b{re.escape(pkg)}\b(?:[<>=!]+[^\s]*)?(?:\[[^\]]*\])?"
                        )  # pkg, pkg>=1.0, pkg[extras], etc.
                        patterns.append(
                            rf"\b{re.escape(pkg)}=[^\s]*"
                        )  # pkg=version
                    else:
                        # For system package managers, handle both direct and python-prefixed versions
                        patterns.append(
                            rf"\b{re.escape(pkg)}\b(?:[<>=!:]+[^\s]*)?"
                        )  # direct package name
                        patterns.append(
                            rf"\bpython-{re.escape(pkg)}\b(?:[<>=!:]+[^\s]*)?"
                        )  # python- prefix
                        patterns.append(
                            rf"\bpython3-{re.escape(pkg)}\b(?:[<>=!:]+[^\s]*)?"
                        )  # python3- prefix

                    for pattern in patterns:
                        modified_line = re.sub(pattern, "", modified_line)

                # Clean up extra spaces that may have been left behind
                modified_line = re.sub(r"\s+", " ", modified_line)
                # Preserve original indentation
                indent = original_line[
                    : len(original_line) - len(original_line.lstrip())
                ]
                modified_line = indent + modified_line.strip()

                # Preserve line continuation backslashes if they were in the original
                # line
                if original_line.rstrip().endswith("\\"):
                    if not modified_line.rstrip().endswith("\\"):
                        modified_line = modified_line.rstrip() + " \\"

                out.append(modified_line)
            else:
                # Original logic for non-conda/system commands
                should_keep = True
                for pkg in unused:
                    # Check if this line contains system packages (python-* pattern)
                    # If so, handle it with system package logic
                    if re.search(r"\bpython-\w+", ln):
                        # This line contains python-prefixed packages, apply system
                        # package removal logic
                        modified_line = ln
                        original_line = ln

                        # Apply system package patterns
                        patterns = []
                        patterns.append(
                            rf"\b{re.escape(pkg)}\b(?:[<>=!:]+[^\s]*)?"
                        )  # direct package name
                        patterns.append(
                            rf"\bpython-{re.escape(pkg)}\b(?:[<>=!:]+[^\s]*)?"
                        )  # python- prefix
                        patterns.append(
                            rf"\bpython3-{re.escape(pkg)}\b(?:[<>=!:]+[^\s]*)?"
                        )  # python3- prefix

                        for pattern in patterns:
                            modified_line = re.sub(pattern, "", modified_line)

                        # Clean up extra spaces and empty python- prefixes
                        modified_line = re.sub(r"\s+", " ", modified_line)
                        modified_line = re.sub(
                            r"\bpython-\s+", "", modified_line
                        )  # Remove empty python- prefixes
                        modified_line = re.sub(
                            r"\bpython3-\s+", "", modified_line
                        )  # Remove empty python3- prefixes
                        # Preserve original indentation
                        indent = original_line[
                            : len(original_line) - len(original_line.lstrip())
                        ]
                        modified_line = indent + modified_line.strip()

                        # Preserve line continuation backslashes
                        if original_line.rstrip().endswith("\\"):
                            if not modified_line.rstrip().endswith("\\"):
                                modified_line = modified_line.rstrip() + " \\"

                        # Replace the line in our output
                        should_keep = False  # We'll add the modified line instead
                        out.append(modified_line)
                        break
                    else:
                        # Regular pattern matching for non-system package lines
                        if (
                            re.search(rf"\b{re.escape(pkg)}\b", ln)
                            and not re.search(rf"\bpython-{re.escape(pkg)}\b", ln)
                            and not re.search(rf"\bpython3-{re.escape(pkg)}\b", ln)
                        ):
                            should_keep = False
                            break
                if should_keep:
                    out.append(ln)

        return out
