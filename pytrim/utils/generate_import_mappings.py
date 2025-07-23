#!/usr/bin/env python3
"""
Generate import name to package name mappings.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from typing import Set


def normalize_name(name: str) -> str:
    """Normalize package/module names."""
    return name.lower().replace("-", "_").replace(".", "_")


def find_toplevels(
    package_name: str, version: str = None, tmp_install_dir: Path = None
) -> Set[str]:
    """Find top_level import names for a given package by installing it."""
    if tmp_install_dir is None:
        tmp_install_dir = Path(tempfile.mkdtemp())
        should_cleanup_parent = True
    else:
        should_cleanup_parent = False

    tmp_install_dir_toplevel = (
        tmp_install_dir / f"{package_name}_{version or 'latest'}_toplevel"
    )

    if not tmp_install_dir_toplevel.exists():
        try:
            tmp_install_dir_toplevel.mkdir(parents=True, exist_ok=True)
        except Exception:
            return set()

        package_spec = f"{package_name}=={version}" if version else package_name
        cmd = [
            "pip3",
            "install",
            "-t",
            str(tmp_install_dir_toplevel),
            "--no-deps",
            package_spec,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                if tmp_install_dir_toplevel.exists():
                    shutil.rmtree(tmp_install_dir_toplevel)
                return set()
        except Exception:
            if tmp_install_dir_toplevel.exists():
                shutil.rmtree(tmp_install_dir_toplevel)
            return set()

    root_path = Path(tmp_install_dir_toplevel)
    top_levels = []
    naked_modules = []

    try:
        # Find packages (directories with __init__.py or namespace packages)
        for subdir in root_path.iterdir():
            if subdir.is_dir() and not subdir.name.endswith(".dist-info"):
                # Check if it's a regular package with __init__.py
                if (subdir / "__init__.py").exists():
                    top_levels.append(subdir.name)
                # Check if it's a namespace package (has .py files or subdirectories)
                elif any(subdir.glob("*.py")) or any(
                    d.is_dir() for d in subdir.iterdir()
                ):
                    top_levels.append(subdir.name)

        # Find naked modules (.py or .so files)
        for item in root_path.iterdir():
            if item.is_file() and (item.suffix == ".py" or item.suffix == ".so"):
                naked_modules.append(item.stem)

        # Combine results
        import_names = set()
        import_names.update(top_levels)
        import_names.update(naked_modules)

        # Filter out invalid names
        valid_names = set()
        for name in import_names:
            if (
                name.isidentifier()
                and not name.startswith("_")
                and not name.endswith(".dist-info")
                and not name.startswith(".")
            ):
                valid_names.add(name)

        return valid_names

    except Exception:
        return set()
    finally:
        # Clean up
        if tmp_install_dir_toplevel.exists():
            try:
                shutil.rmtree(tmp_install_dir_toplevel)
            except Exception:
                pass

        # Clean up parent directory if we created it
        if should_cleanup_parent and tmp_install_dir.exists():
            try:
                shutil.rmtree(tmp_install_dir)
            except Exception:
                pass


def _generate_dynamic_variations(package_name: str) -> set[str]:
    """Generate all possible dynamic variations for a package name."""
    variations = set()

    # Basic variations
    variations.add(normalize_name(package_name))
    variations.add(package_name.replace("-", "_"))
    variations.add(package_name.replace("-", ""))
    variations.add(package_name.replace("_", ""))
    variations.add(package_name.lower())

    # Python-specific transformations
    if "python" in package_name:
        variations.add(package_name.replace("python-", "").replace("-python", ""))

    # Generate abbreviation patterns dynamically
    parts = package_name.lower().replace("-", " ").replace("_", " ").split()

    # Handle compound words within single parts
    if len(parts) == 1 and len(parts[0]) > 6:
        word = parts[0]
        if any(char.isdigit() for char in word):
            base_word = "".join(char for char in word if not char.isdigit())

            # Simple heuristic: try splitting long compound words
            if len(base_word) > 8:
                # Look for likely word boundaries
                for i in range(4, len(base_word) - 3):
                    if (
                        base_word[i - 1] in "aeiou"
                        and base_word[i] not in "aeiou"
                        and i > len(base_word) // 3
                    ):
                        first_part = base_word[:i]
                        second_part = base_word[i:]
                        if len(first_part) >= 4 and len(second_part) >= 3:
                            parts = [first_part, second_part]
                            break

                # Special case patterns
                for pattern in ["soup", "learn"]:
                    if pattern in base_word:
                        pattern_pos = base_word.find(pattern)
                        if pattern_pos > 3:
                            before_pattern = base_word[:pattern_pos]
                            parts = [before_pattern, pattern]
                            break

    if len(parts) > 1:
        # Acronyms
        acronym = "".join(part[0] for part in parts if part)
        if len(acronym) >= 2:
            variations.add(acronym)

        # Shortened versions
        for length in [2, 3]:
            shortened = "".join(part[:length] for part in parts if len(part) >= length)
            if len(shortened) >= 2:
                variations.add(shortened)

        # Combined patterns
        if len(parts) >= 2:
            first_word = parts[0]
            last_word = parts[-1]

            if len(first_word) >= 2 and len(last_word) >= 2:
                # Various combination patterns
                combinations = [
                    first_word[:2] + last_word,
                    first_word[:3] + last_word if len(first_word) >= 3 else None,
                ]

                # Pattern variations
                for last_len in [2, 3, 4]:
                    if len(last_word) >= last_len:
                        combinations.append(first_word + last_word[:last_len])

                for first_len in [2, 3, 4]:
                    if len(first_word) >= first_len:
                        combinations.append(first_word[:first_len] + last_word)

                for combo in combinations:
                    if combo:
                        variations.add(combo)

        # Basic combinations
        variations.add(parts[0])
        variations.add("".join(parts))

        # Number patterns
        if len(parts) >= 2:
            first_word = parts[0]
            if len(first_word) >= 2:
                for i in range(2, 10):
                    variations.add(f"{first_word[:2]}{i}")

            if len(acronym) >= 2:
                for i in range(2, 10):
                    variations.add(f"{acronym}{i}")

        # Letter combinations
        if len(parts) >= 2:
            first_part = parts[0]
            last_part = parts[-1]
            if len(first_part) >= 2 and len(last_part) >= 2:
                variations.add(first_part[:2] + last_part[:2])
                if len(first_part) >= 3:
                    variations.add(first_part[:3] + last_part[0])

        # Consonant patterns
        for part in parts:
            if len(part) >= 4:
                consonants = ""
                for i, char in enumerate(part):
                    if i == 0 or i == len(part) - 1 or char not in "aeiou":
                        consonants += char
                if len(consonants) >= 2:
                    variations.add(consonants)

                first_consonants = ""
                for char in part[:3]:
                    if char not in "aeiou":
                        first_consonants += char
                if len(first_consonants) >= 2 and part[-1] not in "aeiou":
                    variations.add(first_consonants + part[-1])

    # Truncated versions
    for length in [3, 4, 5]:
        if len(package_name) > length:
            variations.add(package_name[:length])

    # Filter valid variations
    valid_variations = set()
    for var in variations:
        if var and len(var) >= 2 and var.replace("_", "").replace(".", "").isalnum():
            valid_variations.add(var)

    return valid_variations


def install_package(package_name: str, venv_python: Path) -> bool:
    """Install package in venv."""
    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", package_name, "--quiet"],
            capture_output=True,
            timeout=120,
        )
        return result.returncode == 0
    except:
        return False


def discover_dynamic_import(venv_python: Path, package_name: str) -> Set[str]:
    """Try dynamic import discovery."""
    import_names = set()

    # Get all dynamic variations
    variations = _generate_dynamic_variations(package_name)

    # Try each variation
    for variation in variations:
        try:
            # Try direct import
            result = subprocess.run(
                [str(venv_python), "-c", f"import {variation}; print('{variation}')"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                import_names.add(variation)
        except:
            continue

    return import_names


def discover_pip_show(venv_python: Path, package_name: str) -> Set[str]:
    """Extract from pip show metadata."""
    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return set()

        # Look for Files: section
        lines = result.stdout.split("\n")
        import_names = set()
        in_files = False

        for line in lines:
            if line.startswith("Files:"):
                in_files = True
                continue
            elif in_files and line.startswith(" "):
                file_path = line.strip()
                if "/" in file_path:
                    module = file_path.split("/")[0]
                    if (
                        module.isidentifier()
                        and not module.startswith("_")
                        and not module.endswith(".dist-info")
                    ):
                        import_names.add(module)
            elif in_files and not line.startswith(" "):
                break

        return import_names
    except:
        return set()


def discover_importlib_metadata(venv_python: Path, package_name: str) -> Set[str]:
    """Extract import names using importlib.metadata (Python 3.8+)."""
    try:
        result = subprocess.run(
            [
                str(venv_python),
                "-c",
                f"""
import importlib.metadata
try:
    dist = importlib.metadata.distribution('{package_name}')
    files = dist.files or []
    import_names = set()

    # Get top-level packages from files
    for file in files:
        parts = str(file).split('/')
        if parts and not parts[0].endswith('.dist-info'):
            top_level = parts[0]
            if '.' not in top_level and top_level.isidentifier():
                import_names.add(top_level)

    # Also try to get from top_level.txt if available
    try:
        top_level_txt = dist.read_text('top_level.txt')
        if top_level_txt:
            for line in top_level_txt.strip().split('\\n'):
                if line.strip():
                    import_names.add(line.strip())
    except:
        pass

    print('\\n'.join(sorted(import_names)))
except Exception as e:
    pass
""",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout.strip():
            import_names = set()
            for line in result.stdout.strip().split("\n"):
                name = line.strip()
                if name and name.isidentifier() and not name.startswith("_"):
                    import_names.add(name)
            return import_names

    except:
        pass
    return set()


def discover_pkg_resources(venv_python: Path, package_name: str) -> Set[str]:
    """Extract import names using pkg_resources (legacy method)."""
    try:
        result = subprocess.run(
            [
                str(venv_python),
                "-c",
                f"""
import pkg_resources
try:
    dist = pkg_resources.get_distribution('{package_name}')
    import_names = set()

    # Try to get top_level.txt
    try:
        top_level = dist.get_metadata('top_level.txt')
        for line in top_level.strip().split('\\n'):
            if line.strip():
                import_names.add(line.strip())
    except:
        pass

    # Fallback: analyze location
    if not import_names and dist.location:
        import os
        import glob
        location = dist.location

        # Look for package directories
        for item in os.listdir(location):
            item_path = os.path.join(location, item)
            if os.path.isdir(item_path) and not item.endswith('.dist-info'):
                if os.path.exists(os.path.join(item_path, '__init__.py')):
                    if item.isidentifier() and not item.startswith('_'):
                        import_names.add(item)
            elif item.endswith('.py') and not item.startswith('_'):
                name = item[:-3]
                if name.isidentifier():
                    import_names.add(name)

    print('\\n'.join(sorted(import_names)))
except Exception as e:
    pass
""",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout.strip():
            import_names = set()
            for line in result.stdout.strip().split("\n"):
                name = line.strip()
                if name and name.isidentifier() and not name.startswith("_"):
                    import_names.add(name)
            return import_names

    except:
        pass
    return set()


def discover_pypi_api(venv_python: Path, package_name: str) -> Set[str]:
    """Extract import names using PyPI JSON API as fallback."""
    try:
        result = subprocess.run(
            [
                str(venv_python),
                "-c",
                f"""
import urllib.request
import json
try:
    url = 'https://pypi.org/pypi/{package_name}/json'
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.load(response)

    import_names = set()

    # Try to extract from project name and normalize
    project_name = data.get('info', {{}}).get('name', '{package_name}')
    normalized = project_name.lower().replace('-', '_').replace('.', '_')
    if normalized.isidentifier():
        import_names.add(normalized)

    # Look for common patterns in description
    description = data.get('info', {{}}).get('description', '').lower()
    summary = data.get('info', {{}}).get('summary', '').lower()

    # Simple heuristic: if package name appears in text, likely matches import
    if any(project_name.lower() in text for text in [description, summary]):
        import_names.add(normalized)

    print('\\n'.join(sorted(import_names)) if import_names else '')
except Exception as e:
    pass
""",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode == 0 and result.stdout.strip():
            import_names = set()
            for line in result.stdout.strip().split("\n"):
                name = line.strip()
                if name and name.isidentifier() and not name.startswith("_"):
                    import_names.add(name)
            return import_names

    except:
        pass
    return set()


def discover_dist_info(venv_python: Path, package_name: str) -> Set[str]:
    """Extract from .dist-info files."""
    try:
        # Get site-packages path
        result = subprocess.run(
            [str(venv_python), "-c", "import site; print(site.getsitepackages()[0])"],
            capture_output=True,
            text=True,
            check=True,
        )

        site_packages = Path(result.stdout.strip())
        import_names = set()

        # Find matching .dist-info
        for dist_info in site_packages.glob("*.dist-info"):
            pkg_name = dist_info.stem.split("-")[0]
            if normalize_name(pkg_name) == normalize_name(package_name):
                # Check top_level.txt
                top_level = dist_info / "top_level.txt"
                if top_level.exists():
                    content = top_level.read_text().strip()
                    for line in content.splitlines():
                        if line.strip():
                            import_names.add(line.strip())
                break

        return import_names
    except:
        return set()


def discover_site_packages(venv_python: Path, package_name: str) -> Set[str]:
    """Analyze site-packages structure."""
    try:
        # Get site-packages path
        result = subprocess.run(
            [str(venv_python), "-c", "import site; print(site.getsitepackages()[0])"],
            capture_output=True,
            text=True,
            check=True,
        )

        site_packages = Path(result.stdout.strip())
        candidates = []

        # Find all Python modules/packages
        for item in site_packages.iterdir():
            if item.name.endswith(".dist-info"):
                continue

            # Only consider Python modules/packages
            if (
                item.is_dir()
                and item.name.isidentifier()
                and not item.name.startswith("_")
            ):
                # Check if it has __init__.py or .py files
                if any(item.glob("*.py")) or (item / "__init__.py").exists():
                    candidates.append(item.name)
            elif (
                item.suffix == ".py"
                and item.stem.isidentifier()
                and not item.stem.startswith("_")
            ):
                candidates.append(item.stem)

        # Score by similarity using dynamic pattern matching
        pkg_norm = normalize_name(package_name)
        dynamic_variations = _generate_dynamic_variations(package_name)
        best_matches = []

        for candidate in candidates:
            cand_norm = normalize_name(candidate)
            score = 0

            # Exact match gets highest score
            if cand_norm == pkg_norm:
                score = 100
            # Check if candidate matches any dynamic variations
            elif candidate.lower() in dynamic_variations:
                score = 95
            # Package name contains candidate or vice versa
            elif pkg_norm in cand_norm or cand_norm in pkg_norm:
                score = 90
            # Start/end match (at least 3 chars)
            elif (
                len(pkg_norm) >= 3
                and len(cand_norm) >= 3
                and (
                    cand_norm.startswith(pkg_norm[:3])
                    or pkg_norm.startswith(cand_norm[:3])
                )
            ):
                score = 70
            # Character overlap
            elif len(set(pkg_norm) & set(cand_norm)) >= min(3, len(pkg_norm) * 0.5):
                score = 50

            if score >= 70:  # Only keep high confidence matches
                best_matches.append((score, candidate))

        # Return best match only
        best_matches.sort(reverse=True)
        if best_matches:
            return {best_matches[0][1]}

        return set()

    except:
        return set()


def get_package_imports(
    package_name: str, temp_venv_path: Path, verbose: bool = False
) -> Set[str]:
    """Get import names for a package using all methods."""
    venv_python = temp_venv_path / "bin" / "python"
    if sys.platform == "win32":
        venv_python = temp_venv_path / "Scripts" / "python.exe"

    # Install package
    if not install_package(package_name, venv_python):
        if verbose:
            print(
                f"  → Installation failed, using fallback: {normalize_name(package_name)}"
            )
        return {normalize_name(package_name)}

    # Try find_toplevels as primary method first
    try:
        toplevel_imports = find_toplevels(
            package_name, None, None
        )  # Let it create its own temp dir
        if toplevel_imports and _is_valid_result(toplevel_imports, package_name):
            if verbose:
                print(f"  → Found: {list(toplevel_imports)} using find_toplevels")
            return toplevel_imports
    except Exception as e:
        if verbose:
            print(f"  → find_toplevels failed: {e}")
        pass

    # Fallback methods if find_toplevels fails
    methods = [
        discover_dist_info,  # Official metadata
        discover_importlib_metadata,  # Modern Python standard library
        discover_pkg_resources,  # Legacy but reliable
        discover_pip_show,  # Pip's own metadata
        discover_pypi_api,  # External API fallback
        discover_dynamic_import,  # Dynamic testing approach
        discover_site_packages,  # Last resort - filesystem analysis
    ]

    for method in methods:
        import_names = method(venv_python, package_name)
        method_name = method.__name__

        # Basic validation - reject obvious junk
        if import_names and _is_valid_result(import_names, package_name):
            final_result = import_names
            if verbose:
                print(f"  → Found: {list(final_result)} using {method_name}")
            return final_result

    # Fallback
    fallback_result = {normalize_name(package_name)}
    if verbose:
        print(f"  → Fallback: {list(fallback_result)} (no methods succeeded)")
    return fallback_result


def _is_valid_result(import_names: Set[str], package_name: str) -> bool:
    """Basic validation of import names."""
    if not import_names:
        return False

    if len(import_names) > 20:
        return False

    # Filter out invalid names but keep the valid ones
    valid_names = set()
    bad_patterns = {"test", "example", "demo", "docs", "bin", "scripts"}

    for name in import_names:
        # Skip single character names
        if len(name) <= 1:
            continue

        # Skip names with bad patterns
        if any(pattern in name.lower() for pattern in bad_patterns):
            continue

        valid_names.add(name)

    # Update the original set with only valid names
    import_names.clear()
    import_names.update(valid_names)

    return len(import_names) > 0


def generate_mappings(
    package_names: list[str], output_file: str = None, verbose: bool = False
):
    """Generate mappings for package list."""
    mappings = {}

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_venv_path = Path(temp_dir) / "temp_venv"
        print("Creating virtual environment...")
        venv.create(temp_venv_path, with_pip=True)

        for i, package_name in enumerate(package_names, 1):
            if verbose:
                print(f"\nProcessing {package_name} ({i}/{len(package_names)})...")
            else:
                print(f"Processing {package_name} ({i}/{len(package_names)})...")

            import_names = get_package_imports(package_name, temp_venv_path, verbose)
            mappings[package_name] = list(import_names)

            # Periodic cleanup
            if i % 10 == 0:
                venv_python = temp_venv_path / "bin" / "python"
                if sys.platform == "win32":
                    venv_python = temp_venv_path / "Scripts" / "python.exe"
                try:
                    subprocess.run(
                        [
                            str(venv_python),
                            "-m",
                            "pip",
                            "uninstall",
                            package_name,
                            "-y",
                            "--quiet",
                        ],
                        capture_output=True,
                    )
                except:
                    pass

    # Only save results if output_file is specified
    if output_file:
        with open(output_file, "w") as f:
            json.dump(mappings, f, indent=2, sort_keys=True)
        print(f"Generated {len(mappings)} mappings -> {output_file}")
    else:
        if verbose:
            print(f"Generated {len(mappings)} mappings (not saved)")

    return mappings


def get_top_packages(count: int = 100) -> list[str]:
    """Get top PyPI packages."""
    try:
        import urllib.request

        url = "https://raw.githubusercontent.com/hugovk/top-pypi-packages/main/top-pypi-packages-30-days.min.json"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.load(response)
            return [pkg["project"] for pkg in data["rows"][:count]]
    except:
        return []


def generate_mappings_from_packages(
    packages: list[str],
    output_file: str = "import_mappings.json",
    verbose: bool = False,
    show_stats: bool = False,
):
    """Generate mappings for specific packages."""
    return generate_mappings(packages, output_file, verbose)


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate import mappings")
    parser.add_argument("--packages", nargs="+", help="Specific packages")
    parser.add_argument("--top", type=int, default=100, help="Top N packages")
    parser.add_argument("--output", default="import_mappings.json", help="Output file")
    parser.add_argument("--from-file", help="Package list file")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.packages:
        packages = args.packages
    elif args.from_file:
        with open(args.from_file) as f:
            packages = [line.strip() for line in f if line.strip()]
    else:
        packages = get_top_packages(args.top)

    generate_mappings(packages, args.output, args.verbose)


if __name__ == "__main__":
    main()
