"""Dependency analysis for finding unused dependencies."""

from pathlib import Path

from ..extractors.dependency_extractor import extract_deps
from ..utils.package_utils import normalize
from .module_analyzer import find_used_modules, get_installed_deps


def find_unused_dependencies(
    py_files: list[str],
    cfg_files: list[str],
    root: str,
    explicit: set[str] = None,
    mappings_file: str = None,
    libraries_to_process: set[str] = None,
) -> dict[str, set[str]]:
    """Find unused dependencies in config files."""
    if explicit:
        # If explicit list provided, only include them if they exist in each config file
        explicit_norm = {normalize(x) for x in explicit}
        result = {}
        for cfg in cfg_files:
            deps = extract_deps(Path(cfg))
            deps_norm = {normalize(x) for x in deps}
            # Only include explicit packages that actually exist in this config file
            result[cfg] = explicit_norm.intersection(deps_norm)
        return result

    # If libraries_to_process is provided, only analyze those
    if libraries_to_process:
        # Still do the actual analysis, but filter to only the specified libraries
        libraries_to_check = {normalize(x) for x in libraries_to_process}
    else:
        # Analyze all dependencies
        libraries_to_check = None

    # Load import mappings
    mappings_path = Path(mappings_file) if mappings_file else None
    installed = get_installed_deps(Path(root), mappings_path)
    used = find_used_modules(py_files)

    # Build a comprehensive view of all declared dependencies across all config files
    all_declared_deps = set()
    for cfg in cfg_files:
        deps = extract_deps(Path(cfg))
        all_declared_deps.update(deps)

    # Ensure mappings for all dependencies
    from .module_analyzer import ensure_mappings

    if mappings_file:
        ensure_mappings(all_declared_deps, mappings_file, verbose=False)
        # Reload mappings after ensuring they exist
        installed = get_installed_deps(Path(root), mappings_path)

    res = {}
    for cfg in cfg_files:
        deps = extract_deps(Path(cfg))
        unused = set()
        for pkg in deps:
            # Skip if libraries_to_check is specified and this package is not in it
            if libraries_to_check and normalize(pkg) not in libraries_to_check:
                continue

            # Get possible import names for this package
            imps = installed.get(normalize(pkg), {normalize(pkg)})
            # Check if any of the import names for this package are actually used
            pkg_is_used = any(i in used for i in imps)

            if not pkg_is_used:
                # Additional check: verify the package isn't required as a transitive dependency
                # by other packages that ARE used. This is a more sophisticated check.
                is_transitive_requirement = False

                # For now, keep the simpler logic but with better import mappings
                # The comprehensive transitive analysis would require more complex dependency graph analysis
                unused.add(pkg)
        res[cfg] = unused
    return res


def get_direct_dependencies(cfg_files: list[str]) -> dict[str, set[str]]:
    """Get direct dependencies from each config file."""
    direct_deps = {}

    for cfg in cfg_files:
        deps = extract_deps(Path(cfg))

        # Filter to only include direct dependencies
        # This is a simplified approach - in reality, we'd need to parse the config files
        # to determine which dependencies are declared as direct vs transitive
        cfg_path = Path(cfg)
        if cfg_path.name in [
            "requirements.txt",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "Pipfile",
        ]:
            # These typically contain direct dependencies
            direct_deps[cfg] = deps
        else:
            # For other files, we might need different logic
            direct_deps[cfg] = deps

    return direct_deps


def find_unused_direct_dependencies(
    py_files: list[str],
    cfg_files: list[str],
    root: str,
    explicit: set[str] = None,
    mappings_file: str = None,
    libraries_to_process: set[str] = None,
) -> dict[str, set[str]]:
    """Find unused direct dependencies only with robust fallback analysis."""

    # If explicit libraries are provided, only include them if they exist in each config file
    if explicit:
        explicit_norm = {normalize(x) for x in explicit}
        result = {}
        for cfg in cfg_files:
            deps = extract_deps(Path(cfg))
            deps_norm = {normalize(x) for x in deps}
            # Only include explicit packages that actually exist in this config file
            result[cfg] = explicit_norm.intersection(deps_norm)
        return result

    # Get direct dependencies from config files
    direct_deps = get_direct_dependencies(cfg_files)

    # Load import mappings and analyze used modules
    mappings_path = Path(mappings_file) if mappings_file else None
    installed = get_installed_deps(Path(root), mappings_path)
    used = find_used_modules(py_files)

    # If libraries_to_process is provided, filter to only analyze those
    if libraries_to_process:
        libraries_to_check = {normalize(x) for x in libraries_to_process}
    else:
        libraries_to_check = None

    # Build comprehensive view of all declared dependencies
    all_declared_deps = set()
    for cfg in cfg_files:
        deps = extract_deps(Path(cfg))
        all_declared_deps.update(deps)

    # Ensure mappings for all dependencies
    from .module_analyzer import ensure_mappings

    if mappings_file:
        ensure_mappings(all_declared_deps, mappings_file, verbose=False)
        # Reload mappings after ensuring they exist
        installed = get_installed_deps(Path(root), mappings_path)

    # Analyze each config file for unused direct dependencies
    filtered_unused = {}
    for cfg in cfg_files:
        deps = extract_deps(Path(cfg))
        unused_direct = set()

        # Only analyze dependencies that are in this config file (direct dependencies)
        for pkg in deps:
            # Skip if libraries_to_check is specified and this package is not in it
            if libraries_to_check and normalize(pkg) not in libraries_to_check:
                continue

            # Get possible import names for this package
            imps = installed.get(normalize(pkg), {normalize(pkg)})

            # Check if any of the import names for this package are actually used
            pkg_is_used = any(i in used for i in imps)

            if not pkg_is_used:
                # This is a direct dependency that appears unused
                unused_direct.add(pkg)

        filtered_unused[cfg] = unused_direct

    return filtered_unused
