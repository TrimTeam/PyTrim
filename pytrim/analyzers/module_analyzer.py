"""Module analysis for finding used modules and installed dependencies."""

import ast
import json
from pathlib import Path

from ..utils.package_utils import normalize


def find_used_modules(py_files: list[str]) -> set[str]:
    """Find all modules imported in Python files."""
    used = set()
    for f in py_files:
        p = Path(f)
        if "venv" in str(p).lower() or "site-packages" in str(p).lower():
            continue
        try:
            tree = ast.parse(p.read_text())
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    for a in n.names:
                        module_name = normalize(a.name.split(".", 1)[0])
                        used.add(module_name)
                elif isinstance(n, ast.ImportFrom) and n.module:
                    module_name = normalize(n.module.split(".", 1)[0])
                    used.add(module_name)
        except Exception:
            continue
    return used


def load_import_mappings(mappings_file: Path | str = None) -> dict[str, set[str]]:
    """Load import mappings from JSON file."""
    if mappings_file:
        mappings_path = (
            Path(mappings_file) if isinstance(mappings_file, str) else mappings_file
        )
        if mappings_path.exists():
            try:
                with open(mappings_path) as f:
                    data = json.load(f)
                    # Convert list values to sets and normalize names
                    return {
                        normalize(pkg): {imp for imp in imports}
                        for pkg, imports in data.items()
                    }
            except (json.JSONDecodeError, Exception):
                pass

    # Return empty dict if no mappings file found - will be auto-generated
    return {}


def ensure_mappings(
    libraries: set[str], mappings_file: str, verbose: bool = False
) -> dict[str, set[str]]:
    """Load mappings and auto-generate any missing ones."""
    mappings = load_import_mappings(mappings_file)

    # Find missing libraries
    missing = [lib for lib in libraries if normalize(lib) not in mappings]

    if missing and mappings_file:
        if verbose:
            print(f"Generating mappings for {len(missing)} missing libraries...")

        # Generate new mappings but don't save to file
        from ..utils.generate_import_mappings import generate_mappings

        new_mappings = generate_mappings(missing, output_file=None, verbose=verbose)

        # Add new mappings to the in-memory mappings dict only
        for pkg, imports in new_mappings.items():
            mappings[normalize(pkg)] = {imp for imp in imports}

        if verbose:
            print(
                f"✓ Generated mappings for {len(new_mappings)} libraries (not saved to file)"
            )

    return mappings


def get_correct_names(
    libraries: set[str], mappings: dict[str, set[str]], file_type: str = "python"

) -> set[str]:
    """Get correct names for libraries based on file type.

    Args:
        libraries: Set of library names
        mappings: Import mappings dictionary
        file_type: "python" for import names, "config" for package names

    Returns:
        Set of correctly named libraries
    """
    if file_type == "config":
        # For config files, use normalized package names to match remover expectations
        return {normalize(lib) for lib in libraries}

    # For Python files, convert to import names
    import_names = set()
    for lib in libraries:
        normalized_lib = normalize(lib)
        if normalized_lib in mappings:
            import_names.update(mappings[normalized_lib])
        else:
            # Fallback to library name if mapping not found
            import_names.add(lib)

    return import_names


def get_installed_deps(root: Path, mappings_file: Path = None) -> dict[str, set[str]]:
    """Get mapping of installed packages to their importable modules."""
    pkg_dir = next(root.rglob("*site-packages*"), None)

    # Load mappings from JSON or use defaults
    common_mappings = load_import_mappings(mappings_file)

    out = {}

    if pkg_dir:
        # Read from actual site-packages if available
        for info in pkg_dir.glob("*.dist-info"):
            name = normalize(info.stem.split("-", 1)[0])
            tl = info / "top_level.txt"
            mods = set()
            if tl.exists():
                for m in tl.read_text().splitlines():
                    mods.add(normalize(m))
            out[name] = mods or {name}

    # Add common mappings for packages not found in site-packages
    for pkg_name, import_names in common_mappings.items():
        if pkg_name not in out:  # pkg_name is already normalized
            out[pkg_name] = import_names

    return out
