"""PyTrim - Trim unused dependencies from Python projects.

A professional tool for trimming unused imports and dependencies from Python code
and configuration files.
"""

__version__ = "1.0.0"
__author__ = "Trim Team"
__email__ = "dinoskarakas@gmail.com"
__description__ = "Auto-detect and trim unused dependencies from Python projects"

# Core functionality
try:
    from .analyzers import (
        find_unused_dependencies,
        find_used_modules,
        get_installed_deps,
    )
    from .cli.cli import main
    from .core import create_dir_report, create_project_report, trim_file
    from .extractors.dependency_extractor import extract_deps
    from .removers import remove_package_from_line, remove_unused_dependencies
    from .utils import (
        ConfigFilePatterns,
        discover_config_files,
        discover_python_files,
        normalize,
    )
except ImportError:
    # During installation, modules might not be available yet
    pass

__all__ = [
    # Core functions
    "trim_file",
    "create_dir_report",
    "create_project_report",
    # Analysis functions
    "find_unused_dependencies",
    "find_used_modules",
    "get_installed_deps",
    # Removal functions
    "remove_unused_dependencies",
    "remove_package_from_line",
    # Extraction functions
    "extract_deps",
    # Utilities
    "normalize",
    "ConfigFilePatterns",
    "discover_config_files",
    "discover_python_files",
    # CLI
    "main",
    # Metadata
    "__version__",
    "__author__",
    "__email__",
    "__description__",
]
