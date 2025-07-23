"""Shell files dependency extractor."""

from pathlib import Path
from typing import Set

from ..utils.package_utils import normalize
from .base import BaseExtractor


class ShellFileExtractor(BaseExtractor):
    """Extractor for shell script files (.sh)."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is a shell file."""
        return file_path.suffix == ".sh"

    def extract(self, file_path: Path, seen: Set[Path] = None) -> Set[str]:
        """Extract dependencies from shell files."""
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
        lines = text.splitlines()
        in_multiline_install = False
        multiline_install_type = None

        for ln in lines:
            s = ln.strip()

            # Check if we're starting a new install command
            if any(
                pkg_mgr in s
                for pkg_mgr in [
                    "apt-get install",
                    "apt install",
                    "yum install",
                    "dnf install",
                    "pacman -S",
                    "brew install",
                ]
            ):
                in_multiline_install = True
                multiline_install_type = "system"
            elif "pip install" in s:
                in_multiline_install = True
                multiline_install_type = "pip"
            elif "conda install" in s or "conda create" in s:
                in_multiline_install = True
                multiline_install_type = "conda"

            # Process packages based on install type
            if in_multiline_install:
                if multiline_install_type == "pip":
                    out.update(self._extract_pip_packages(s, in_multiline_install))
                elif multiline_install_type == "conda":
                    out.update(self._extract_conda_packages(s, in_multiline_install))
                elif multiline_install_type == "system":
                    out.update(self._extract_system_packages(s, in_multiline_install))

            # Check if we're ending the multiline command (no backslash at end)
            if in_multiline_install and not ln.rstrip().endswith("\\"):
                in_multiline_install = False
                multiline_install_type = None

        return out

    def _extract_pip_packages(self, line: str, in_multiline: bool) -> Set[str]:
        """Extract packages from pip install commands."""
        out = set()
        if "pip install" in line or in_multiline:
            parts = line.split("pip install") if "pip install" in line else [line]
            pkg_part = parts[-1].strip() if parts else line
            for pkg in pkg_part.split():
                if not pkg.startswith("-") and pkg not in ["--", "&&", "||", "\\"]:
                    out.add(normalize(pkg.split("==")[0].split(">=")[0].split("<=")[0]))
        return out

    def _extract_conda_packages(self, line: str, in_multiline: bool) -> Set[str]:
        """Extract packages from conda install/create commands."""
        out = set()
        if (
            any(cmd in line for cmd in ["conda install", "conda create"])
            or in_multiline
        ):
            parts = line.split()
            skip_next = False

            for part in parts:
                if skip_next:
                    skip_next = False
                    continue

                # Skip command and common flags
                if part in [
                    "conda",
                    "install",
                    "create",
                    "-q",
                    "-y",
                    "--yes",
                    "--quiet",
                ]:
                    continue
                elif part.startswith("-"):
                    # Skip flags, some may have values
                    if part in ["-n", "-c", "--name", "--channel", "--prefix", "-p"]:
                        skip_next = True  # Skip the next argument (flag value)
                    continue
                elif "=" in part and not part.startswith("-"):
                    # This could be python=3.8 or $VAR=value, extract package name
                    pkg_name = part.split("=")[0].strip()
                    if (
                        pkg_name
                        and not pkg_name.startswith("$")
                        and pkg_name != "python"
                    ):
                        out.add(normalize(pkg_name))
                elif (
                    part
                    and not part.startswith("$")
                    and not part.startswith("-")
                    and part not in ["&&", "||", "\\"]
                ):
                    # Regular package name
                    pkg_clean = (
                        part.split("==")[0]
                        .split(">=")[0]
                        .split("<=")[0]
                        .split(">")[0]
                        .split("<")[0]
                    )
                    if pkg_clean and pkg_clean not in ["python"]:
                        out.add(normalize(pkg_clean))
        return out

    def _extract_system_packages(self, line: str, in_multiline: bool) -> Set[str]:
        """Extract packages from system package manager commands."""
        out = set()
        if (
            any(
                pkg_mgr in line
                for pkg_mgr in [
                    "apt-get install",
                    "apt install",
                    "yum install",
                    "dnf install",
                    "pacman -S",
                    "brew install",
                ]
            )
            or in_multiline
        ):
            parts = line.split()
            skip_next = False
            in_install_cmd = False

            # If this line doesn't contain the install command, we're in a continued
            # line
            if not any(
                pkg_mgr in line
                for pkg_mgr in [
                    "apt-get install",
                    "apt install",
                    "yum install",
                    "dnf install",
                    "pacman -S",
                    "brew install",
                ]
            ):
                in_install_cmd = (
                    True  # We're already in the install command from previous line
                )

            for part in parts:
                if skip_next:
                    skip_next = False
                    continue

                # Check if we're in an install command
                if part in ["apt-get", "apt", "yum", "dnf", "pacman", "brew"]:
                    continue
                elif part in ["install", "-S"]:  # -S is for pacman
                    in_install_cmd = True
                    continue
                elif not in_install_cmd:
                    continue
                elif part.startswith("-"):
                    # Skip flags, some may have values
                    if part in [
                        "-y",
                        "--yes",
                        "--assume-yes",
                        "-q",
                        "--quiet",
                        "-f",
                        "--force",
                    ]:
                        continue
                    elif part in ["-t", "--target-release"]:
                        skip_next = True  # Skip the next argument (flag value)
                    continue
                elif (
                    part
                    and not part.startswith("$")
                    and not part.startswith("-")
                    and part not in ["&&", "||", "\\"]
                ):
                    # Regular package name
                    pkg_clean = (
                        part.split("=")[0].split(":")[0].strip()
                    )  # Remove version/arch info
                    if (
                        pkg_clean and "/" not in pkg_clean and len(pkg_clean) > 1
                    ):  # Skip paths and single characters
                        # Convert system package names to Python package names where
                        # possible
                        if pkg_clean.startswith("python-"):
                            python_pkg = pkg_clean[7:]  # Remove 'python-' prefix
                            if python_pkg:  # Make sure it's not empty
                                out.add(normalize(python_pkg))
                        elif pkg_clean.startswith("python3-"):
                            python_pkg = pkg_clean[8:]  # Remove 'python3-' prefix
                            if python_pkg:  # Make sure it's not empty
                                out.add(normalize(python_pkg))
                        else:
                            # Add other packages that are clearly Python-related
                            if any(
                                term in pkg_clean.lower()
                                for term in ["python", "py-", "lib"]
                            ) or pkg_clean in ["cython", "ipython"]:
                                out.add(normalize(pkg_clean))
        return out
