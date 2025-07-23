"""File pattern utilities for config file discovery."""

import re
from pathlib import Path
from typing import List


class ConfigFilePatterns:
    """Manages patterns for identifying different types of config files."""

    # Requirements files patterns
    REQUIREMENTS_PATTERNS = [
        r"[a-zA-Z0-9_-]*requirements[a-zA-Z0-9_-]*\.(?:txt|in)",
        r"requirements\.(?:txt|in)",
        r"constraints\.(?:txt|in)",
    ]

    # Python packaging files
    PYTHON_PACKAGING_PATTERNS = [
        r"pyproject\.toml",
        r"setup\.cfg",
        r"setup\.py",
        r"Pipfile",
    ]

    # Environment and dependency files
    ENVIRONMENT_PATTERNS = [
        r"environment\.(?:yml|yaml)",
        r"meta\.yaml",  # conda-recipe/meta.yaml
        r"\.travis\.yml",  # Travis CI configuration
    ]

    # Documentation files - ONLY specific dependency-related files
    DOCUMENTATION_PATTERNS = [
        r"README\.rst$",  # README files
        r"CHANGELOG\.md$",  # Changelog files
        r"docs/.*\.rst$",  # Documentation files in docs directory
        r".*docs/.*\.rst$",  # Documentation files anywhere
    ]

    # System and container files - ONLY specific config files
    SYSTEM_PATTERNS = [
        r".*\.sh",  # Shell scripts
        r"Dockerfile.*",  # Docker files (including Dockerfile.prod, Dockerfile.dev, etc.)
        r".*\.dockerfile$",  # Alternative dockerfile naming
        r"tox\.ini$",  # Tox configuration (exact match)
        # Remove dangerous .*\.sh pattern that matches ALL shell scripts
    ]

    # Special package files
    PACKAGE_INFO_PATTERNS = [
        r".*\.egg-info/requires\.txt",  # Egg-info requirements
    ]

    @classmethod
    def get_all_patterns(cls) -> List[str]:
        """Get all config file patterns combined."""
        return (
            cls.REQUIREMENTS_PATTERNS
            + cls.PYTHON_PACKAGING_PATTERNS
            + cls.ENVIRONMENT_PATTERNS
            + cls.DOCUMENTATION_PATTERNS
            + cls.SYSTEM_PATTERNS
            + cls.PACKAGE_INFO_PATTERNS
        )

    @classmethod
    def create_compiled_pattern(cls) -> re.Pattern:
        """Create a compiled regex pattern for all config files."""
        all_patterns = cls.get_all_patterns()
        combined_pattern = r"^(" + "|".join(all_patterns) + r")$"
        return re.compile(combined_pattern, re.IGNORECASE)

    @classmethod
    def is_config_file(cls, file_path: Path) -> bool:
        """Check if a file matches any config file pattern."""
        pattern = cls.create_compiled_pattern()
        # Use full path for files that need full path matching (e.g., docs/index.rst)
        full_path_str = str(file_path)
        return bool(pattern.match(file_path.name) or pattern.match(full_path_str))

    @classmethod
    def is_requirements_file(cls, file_path: Path) -> bool:
        """Check if a file is in a requirements directory with .txt or .in extension."""
        req_keywords = ["requirements", "reqs", "req"]
        return any(
            keyword in part.lower()
            for part in file_path.parts
            for keyword in req_keywords
        ) and file_path.suffix.lower() in (".txt", ".in")

    @classmethod
    def should_exclude_file(cls, file_path: Path) -> bool:
        """Check if a file should be excluded from processing."""
        exclude_words = ["changelog", "contributors", "readme"]
        return any(word in file_path.name.lower() for word in exclude_words)

    @classmethod
    def should_exclude_directory(cls, file_path: Path) -> bool:
        """Check if a file is in an excluded directory."""
        path_str = str(file_path).lower()
        return "venv" in path_str or "site-packages" in path_str


def discover_config_files(root: Path) -> List[Path]:
    """Discover all config files in a project directory using safe allowlist."""
    patterns = ConfigFilePatterns()
    cfg_files = []

    # Safe allowlist of config files that actually contain dependencies
    safe_config_files = {
        "requirements.txt",
        "requirements.in",
        "requirements-dev.txt",
        "requirements-test.txt",
        "constraints.txt",
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "Pipfile",
        "environment.yml",
        "environment.yaml",
        "meta.yaml",
        ".travis.yml",
        "Dockerfile",
        "tox.ini",
        "bootstrap.sh",
    }

    for file_path in root.rglob("*"):
        # Skip directories and excluded directories
        if not file_path.is_file() or patterns.should_exclude_directory(file_path):
            continue

        # Only process files in our safe allowlist
        if file_path.name in safe_config_files:
            cfg_files.append(file_path)
        # Also check requirements files in subdirectories
        elif patterns.is_requirements_file(file_path):
            if not patterns.should_exclude_file(file_path):
                cfg_files.append(file_path)

    return cfg_files


def discover_python_files(root: Path) -> List[Path]:
    """Discover all Python files in a project directory, excluding setup.py and virtual environments."""
    py_files = []

    for file_path in root.rglob("*.py"):
        # Exclude setup.py and files in virtual environments
        if (
            file_path.name != "setup.py"
            and "venv" not in str(file_path).lower()
            and "site-packages" not in str(file_path).lower()
        ):
            py_files.append(file_path)

    return py_files
