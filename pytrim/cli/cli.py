import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from importlib import metadata
from pathlib import Path

import colorama

from ..analyzers.dependency_analyzer import find_unused_direct_dependencies
from ..analyzers.module_analyzer import ensure_mappings, get_correct_names
from ..core import file_remover
from ..core.report_producer import (
    clear_reports_directory,
    create_dir_report,
    create_project_report,
)
from ..extractors.dependency_extractor import extract_deps
from ..removers.config_file_remover import remove_unused_dependencies
from ..utils.file_patterns import discover_config_files, discover_python_files
from ..utils.verbose_output import formatter
from .analysis_strategy import create_analysis_chain


def detect_lock_files(project_root):
    """Find all .lock files in the project root."""
    project_path = Path(project_root)
    lock_files = list(project_path.glob("*.lock"))
    return [f.name for f in lock_files]


def get_version():
    try:
        return metadata.version("pytrim")
    except metadata.PackageNotFoundError:
        return "0.1.0-dev"  # Fallback for development


def _is_virtual_environment(path: Path) -> bool:
    """Check if a directory is a Python virtual environment."""
    # Check for pyvenv.cfg (most reliable indicator)
    if (path / "pyvenv.cfg").exists():
        return True

    # Check for activation scripts
    if (path / "bin" / "activate").exists() or (
        path / "Scripts" / "activate.bat"
    ).exists():
        return True

    # Check for site-packages directory structure
    lib_dir = path / "lib"
    if lib_dir.exists():
        for subdir in lib_dir.iterdir():
            if (
                subdir.is_dir()
                and subdir.name.startswith("python")
                and (subdir / "site-packages").exists()
            ):
                return True

    return False


def _is_in_excluded_directory(file_path: Path, root: Path) -> bool:
    """Check if a file is in a directory that should be excluded from processing.

    This function excludes:
    - Test directories (test, tests, testing, __pycache__)
    - Temporary directories (tmp, temp, .git, .cache, .pytest_cache)
    - Virtual environments (detected by pyvenv.cfg, activation scripts, or site-packages)
    - Build directories (build, dist, .tox, .coverage)
    - IDE directories (.idea, .vscode, .mypy_cache)

    But allows legitimate project subdirectories like src/, lib/, etc.
    """
    # Get the relative path from the root
    try:
        rel_path = file_path.relative_to(root)
    except ValueError:
        # File is not under root, exclude it
        return True

    # Check each part of the path for excluded directories
    excluded_dirs = {
        "test",
        "tests",
        "testing",
        "__pycache__",
        "tmp",
        "temp",
        ".git",
        ".cache",
        ".pytest_cache",
        "build",
        "dist",
        ".tox",
        ".coverage",
        ".idea",
        ".vscode",
        ".mypy_cache",
        "node_modules",
        ".github",
        ".gitlab",
        ".circleci",
        ".travis",
        "site-packages",
        "egg-info",
    }

    # Check if any part of the path is in the excluded directories
    for part in rel_path.parts[:-1]:  # Exclude the filename itself
        if part.lower() in excluded_dirs:
            return True

    # Check if any directory in the path is a virtual environment
    current_path = root
    for part in rel_path.parts[:-1]:  # Exclude the filename itself
        current_path = current_path / part
        if _is_virtual_environment(current_path):
            return True

    return False


def _get_mappings_file(args, root):
    """Get path to mappings file to use."""
    if hasattr(args, "mappings_file") and args.mappings_file:
        return args.mappings_file

    # Check local project first
    local_mappings = root / "import_mappings.json"
    if local_mappings.exists():
        return str(local_mappings)

    # Use built-in mappings
    try:
        import pytrim

        package_dir = Path(pytrim.__file__).parent
        builtin_mappings = package_dir / "utils" / "import_mappings.json"
        if builtin_mappings.exists():
            return str(builtin_mappings)
    except ImportError:
        pass

    # Fallback: create empty local file
    return str(local_mappings)


def print_banner():
    """Print the ASCII art banner"""
    banner = """
╔════════════════════════════════════════════════════════╗
║                                                        ║
║    ██████╗ ██╗   ██╗████████╗██████╗ ██╗███╗   ███╗    ║
║    ██╔══██╗╚██╗ ██╔╝╚══██╔══╝██╔══██╗██║████╗ ████║    ║
║    ██████╔╝ ╚████╔╝    ██║   ██████╔╝██║██╔████╔██║    ║
║    ██╔═══╝   ╚██╔╝     ██║   ██╔══██╗██║██║╚██╔╝██║    ║
║    ██║        ██║      ██║   ██║  ██║██║██║ ╚═╝ ██║    ║
║    ╚═╝        ╚═╝      ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝    ║
║                                                        ║
║      Trim unused Python imports and dependencies       ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
"""
    print(banner)


class CustomHelpFormatter(argparse.HelpFormatter):
    def format_help(self):
        print_banner()
        return super().format_help()


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # Customize error output with red color
        print(
            colorama.Fore.RED + f"pytrim: error: {message}" + colorama.Style.RESET_ALL
        )
        self.exit(2)


def main():
    parser = CustomArgumentParser(
        description="Trim unused Python imports and dependencies. Run 'trim' or 'pytrim' in your project directory to get started.",
        formatter_class=CustomHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--file", help="Single Python file to trim.")
    group.add_argument("-d", "--directory", help="Directory of Python files to trim.")
    group2 = parser.add_mutually_exclusive_group()
    group.add_argument(
        "project",
        nargs="?",
        default=".",
        help="Project path to trim (default: current directory). Use 'trim' with no args to trim current project.",
    )
    parser.add_argument(
        "-u",
        "--unused-imports",
        nargs="+",
        help="Specific packages to remove (optional - auto-detects if not specified).",
    )
    parser.add_argument(
        "-r",
        "--report",
        action="store_true",
        help="Generate Markdown reports (to 'reports/').",
    )
    parser.add_argument(
        "-o",
        "--output",
        action="store_true",
        help="Create new debloated files (to 'pytrim_output/') instead of overwriting originals.",
    )
    parser.add_argument(
        "-pr",
        "--pull-request",
        action="store_true",
        help="Create a GitHub PR with the changes (requires gh CLI).",
    )
    group2.add_argument(
        "-dp",
        "--deptry",
        action="store_true",
        help="Use deptry to find unused imports (requires deptry installed).",
    )
    group2.add_argument(
        "-fd",
        "--fawltydeps",
        action="store_true",
        help="Use fawltydeps to find unused dependencies (requires fawltydeps installed).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed information about the trimming process.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"PyTrim {get_version()}"
    )
    parser.add_argument(
        "-gm",
        "--generate-mappings",
        nargs="*",
        help="Generate import mappings JSON file for specified packages (or use discovered packages if none specified).",
    )
    parser.add_argument(
        "-mf",
        "--mappings-file",
        help="Use custom import mappings JSON file instead of built-in mappings.",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        nargs="+",
        help="Exclude specific dependencies from the removal process."
        "E.g. a transitive dependency that needs its version pinned.",
    )
    args = parser.parse_args()

    root = Path(args.project)

    # Show welcome message in verbose mode
    if args.verbose:
        formatter.section("PYTRIM VERBOSE MODE", colorama.Fore.GREEN)
        formatter.info(f"PyTrim v{get_version()} - Python Import & Dependency Trimmer")
        formatter.info(f"Working directory: {Path(args.project).absolute()}")

        # Show selected options
        options = []
        if args.file:
            options.append(f"Single file mode: {args.file}")
        elif args.directory:
            options.append(f"Directory mode: {args.directory}")
        else:
            options.append("Project mode")

        if args.report:
            options.append("Generate reports")
        if args.output:
            options.append("Create output directory")
        if args.pull_request:
            options.append("Create pull request")
        if args.generate_mappings is not None:
            options.append("Generate mappings")

        if options:
            options_line = " | ".join(options)
            formatter.info(f"Active options: {options_line}")

        # Show excluded packages if any
        if args.exclude:
            exclude_list = ", ".join(args.exclude)
            formatter.info(f"Excluded packages: {exclude_list}")

        # Show detection method
        detection_method = "Call graph analysis (default)"
        if args.unused_imports:
            detection_method = f"Manual specification: {args.unused_imports}"
        elif args.deptry:
            detection_method = "Deptry analysis"
        elif args.fawltydeps:
            detection_method = "FawltyDeps analysis"
        elif args.file or args.directory:
            detection_method = "Ruff linter analysis"

        formatter.info(f"Detection method: {detection_method}")

        # Show mappings info
        if args.generate_mappings is not None:
            formatter.info("Will generate custom import mappings on-the-fly")
        else:
            mappings_file = _get_mappings_file(args, root)
            if "import_mappings.json" in mappings_file:
                formatter.info("Using built-in import mappings")
            else:
                formatter.info(f"Using custom import mappings: {mappings_file}")

    packages = set()
    if args.project:
        cfg_files = discover_config_files(root)
        if len(cfg_files) == 0 or all(
            len(p.read_text(encoding="utf-8").strip()) == 0 for p in cfg_files
        ):
            print(
                colorama.Fore.RED
                + "0 configuration files found or they are empty. Use flag -d or -f instead."
                + colorama.Style.RESET_ALL
            )
            sys.exit()
    # Handle mapping generation
    if args.generate_mappings is not None:
        if args.verbose:
            formatter.section("MAPPING GENERATION")
            formatter.info(
                "Generate mappings flag detected - creating custom import mappings"
            )

        from pytrim.utils.generate_import_mappings import (
            generate_mappings_from_packages,
        )

        if args.generate_mappings:
            packages = args.generate_mappings
            if args.verbose:
                formatter.package_list("Using specified packages", packages)
        else:
            py_files = discover_python_files(root)
            for cfg in cfg_files:
                packages.update(extract_deps(Path(cfg)))
            packages = list(packages)

            if args.verbose:
                formatter.package_list("Discovered packages from project", packages)

        output_file = "import_mappings.json"
        if args.verbose:
            formatter.info(f"Generating mappings to: {output_file}")
        else:
            print(
                f"\nGenerating custom import mappings for {len(packages)} packages..."
            )

        generate_mappings_from_packages(packages, output_file, args.verbose)

        if args.verbose:
            formatter.success(f"Import mappings saved to {output_file}")
            formatter.info("Will use generated mappings for this analysis")
        else:
            print(f"✓ Import mappings saved to {output_file}")

        # Set the generated mappings file to be used for the analysis
        args.mappings_file = output_file
    else:
        for cfg in cfg_files:
            packages = extract_deps(Path(cfg))
    # Show dependency detection section if verbose
    if args.verbose:
        formatter.section("DEPENDENCY DETECTION")

    if args.unused_imports:
        # User provided specific packages
        libraries_to_process = set(args.unused_imports)
        if args.verbose:
            formatter.info("Using manually specified dependencies")
    elif args.file:
        if not Path(args.file).exists():
            sys.exit(
                colorama.Fore.RED
                + f"File not found: {args.file}"
                + colorama.Style.RESET_ALL
            )
        if args.verbose:
            formatter.info(f"Analyzing single file: {args.file}")
        libraries_to_process = find_unused_imports_in_file(args.file)
    elif args.directory:
        if not Path(args.directory).exists():
            sys.exit(
                colorama.Fore.RED
                + f"Directory not found: {args.directory}"
                + colorama.Style.RESET_ALL
            )
        all_py_files = list(Path(args.directory).glob("*.py"))
        if args.verbose:
            formatter.info(
                f"Analyzing directory: {args.directory} ({len(all_py_files)} Python files)"
            )
        libraries_to_process = set()
        for py_file in all_py_files:
            libraries_to_process.update(find_unused_imports_in_file(py_file))
    else:
        root = Path(args.project)
        cfg_files = discover_config_files(root)
        try:
            chain = create_analysis_chain(args)
            libraries_to_process = chain.execute(
                file=args.file,
                directory=args.directory,
                project=args.project,
                verbose=args.verbose,
                cfg_files=cfg_files,
            )
        except RuntimeError as e:
            print(
                colorama.Fore.RED
                + f"All analysis methods failed: {e}"
                + colorama.Style.RESET_ALL
            )
            sys.exit(1)
        except Exception as e:
            print(
                colorama.Fore.RED
                + f"Unexpected error during analysis: {e}"
                + colorama.Style.RESET_ALL
            )
            sys.exit(1)
    if libraries_to_process is not None and "" in libraries_to_process:
        libraries_to_process.remove("")
    colorama.init(autoreset=True)
    if args.exclude:
        libraries_to_process.remove(*args.exclude)

    # Show results from dependency detection
    if args.verbose:
        if libraries_to_process:
            formatter.package_list(
                "Found unused dependencies", list(libraries_to_process)
            )
        else:
            formatter.info("No unused dependencies detected")
    # In non-verbose mode, don't show anything during processing - only final result
    root = Path(args.project)

    # if unused libraries are empty, then we don't need import name mapping
    # Process libraries: check mappings and generate missing ones
    if len(libraries_to_process) != 0:
        mappings_file = _get_mappings_file(args, root)
        mappings = ensure_mappings(libraries_to_process, mappings_file, args.verbose)
        # Get correct names for Python files (import names)
        unused = get_correct_names(libraries_to_process, mappings, file_type="python")
        if args.verbose and (libraries_to_process or unused):
            formatter.section("ANALYSIS PHASE")
            # Only show if different from libraries_to_process
            if unused != libraries_to_process:
                formatter.package_list("Import names for Python files", sorted(unused))
    else:
        unused = set()

    # Clear reports directory if report generation is requested
    if args.report:
        clear_reports_directory("pytrim_reports")

    # Discover files
    if args.file:
        py_files, cfg_files = [Path(args.file)], []
    elif args.directory:
        all_py_files = list(Path(args.directory).glob("*.py"))
        # Separate setup.py files from regular Python files
        py_files = [f for f in all_py_files if f.name != "setup.py"]
        cfg_files = []
    else:
        root = Path(args.project)
        py_files = discover_python_files(root)
        # cfg_files already discovered in analysis section above
        # Filter out config files from test and temporary directories
        cfg_files = [f for f in cfg_files if not _is_in_excluded_directory(f, root)]
        if args.verbose and (libraries_to_process or unused):
            formatter.subsection("File Discovery")
            formatter.file_list(
                "Config files (excluding test/temp directories)", cfg_files, root
            )

    # Process Python files (only if there are unused imports to remove)
    files_modified = 0
    if unused:
        if args.verbose:
            formatter.subsection("Processing Python Files")

        # First pass: find files that actually need processing
        files_to_process = []
        for p in py_files:
            try:
                code = p.read_text(encoding="utf-8")
                tree = file_remover.ast.parse(code)
                if file_remover.file_contains_unused_imports(tree, unused):
                    files_to_process.append(p)
            except Exception as e:
                if args.verbose:
                    formatter.skipping_file(str(p), str(e))

        # Second pass: process only files that need changes
        if files_to_process:
            if args.verbose:
                formatter.info(f"Processing {len(files_to_process)} Python files...")
                for p in files_to_process:
                    formatter.processing_file(str(p))
                    file_remover.debloat_file(
                        str(p),
                        unused,
                        args.verbose,
                        args.report,
                        create_debloated=args.output,
                        root=root,
                        reports_dir="pytrim_reports",
                    )
                    files_modified += 1
                formatter.info(f"Modified {files_modified} Python files")
            else:
                # Non-verbose: just process files silently
                for p in files_to_process:
                    file_remover.debloat_file(
                        str(p),
                        unused,
                        args.verbose,
                        args.report,
                        create_debloated=args.output,
                        root=root,
                        reports_dir="pytrim_reports",
                    )
                    files_modified += 1
        else:
            if args.verbose:
                formatter.info("No Python files contain the specified unused imports")
    else:
        if args.verbose:
            formatter.info("No Python files to process - no unused imports found")

    # Process config files (project mode and directory mode)
    if not args.file and not args.directory:
        root = Path(args.directory) if args.directory else Path(args.project)
        mappings_file = _get_mappings_file(args, root)

        if libraries_to_process:
            if args.verbose:
                formatter.subsection("Processing Configuration Files")
            unused_cfg_packages = get_correct_names(
                libraries_to_process, mappings, file_type="config"
            )
            unused_cfg = find_unused_direct_dependencies(
                [str(p) for p in py_files],
                [str(p) for p in cfg_files],
                str(root),
                unused_cfg_packages,
                mappings_file,
                libraries_to_process,
            )

            if args.verbose:
                formatter.info(
                    f"Removing packages from config files: {sorted(unused_cfg_packages)}"
                )

            remove_unused_dependencies(
                [str(p) for p in cfg_files], unused_cfg, args.output, root=root
            )

            # Filter unused_cfg to only include files that were actually processed
            processed_files = {str(p) for p in cfg_files}
            unused_cfg = {k: v for k, v in unused_cfg.items() if k in processed_files}

            # Count unique dependencies removed across all files
            unique_deps_removed = set()
            for deps in unused_cfg.values():
                unique_deps_removed.update(deps)
            deps_removed = len(unique_deps_removed)

            if deps_removed > 0:
                if deps_removed == 1:
                    dep_word = "dependency"
                else:
                    dep_word = "dependencies"
                print(
                    colorama.Fore.YELLOW
                    + f"Removed {deps_removed} {dep_word} {unique_deps_removed} from configuration files"
                    + colorama.Style.RESET_ALL
                )
            else:
                formatter.info("No dependencies removed from configuration files")
        else:
            unused_cfg = {}
            if args.verbose:
                formatter.info(
                    "No configuration files to process - no unused dependencies found"
                )
    else:
        unused_cfg = {}

    # Generate reports if requested
    if args.report:
        if args.verbose:
            formatter.info("Generating reports...")
            if args.directory:
                create_dir_report("pytrim_reports")
            if not args.file and not args.directory:
                create_project_report("pytrim_reports", unused_cfg)
        else:
            # Non-verbose: generate reports silently
            if args.directory:
                create_dir_report("pytrim_reports")
            if not args.file and not args.directory:
                create_project_report("pytrim_reports", unused_cfg)

        if not args.file and not args.directory and args.pull_request:
            root = Path(args.project)
            rpt_dir = root / "pytrim_reports"
            pr_file = rpt_dir / "project_report.md"
            dest = root / "project_report.md"
            pr_file.replace(dest)
            shutil.rmtree(rpt_dir)

            repo = root
            branch = f"debloat/{datetime.now().strftime('%Y%m%d%H%M%S')}"
            if not (repo / ".git").exists():
                print(
                    colorama.Fore.RED
                    + f"Error: {repo} is not a git repository."
                    + colorama.Style.RESET_ALL
                )
                sys.exit(1)
            if not shutil.which("git") or not shutil.which("gh"):
                print(
                    colorama.Fore.RED
                    + "Error: 'git' and 'gh' CLI required for PR creation"
                    + colorama.Style.RESET_ALL
                )
                sys.exit(1)
            try:
                subprocess.run(["git", "checkout", "-b", branch], cwd=repo, check=True)
                subprocess.run(["git", "add", "."], cwd=repo, check=True)
                subprocess.run(
                    ["git", "commit", "-m", "Debloat imports & configs"],
                    cwd=repo,
                    check=True,
                )
                subprocess.run(
                    ["git", "push", "-u", "origin", branch], cwd=repo, check=True
                )
                subprocess.run(
                    [
                        "gh",
                        "pr",
                        "create",
                        "--title",
                        "Debloat imports & configs",
                        "--body-file",
                        str(dest),
                    ],
                    cwd=repo,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                print(colorama.Fore.RED + f"Error: {e}" + colorama.Style.RESET_ALL)
                sys.exit(1)

    # Show success message only if changes were made
    total_files_modified = files_modified if "files_modified" in locals() else 0
    total_removed_deps = (
        sum(len(deps) for deps in unused_cfg.values()) if unused_cfg else 0
    )
    changes_made = total_files_modified > 0 or total_removed_deps > 0

    if changes_made:
        if not (args.file or args.directory):
            success_msg = "Project trimmed successfully!"
        else:
            file_word = "file" if total_files_modified == 1 else "files"
            success_msg = f"{total_files_modified} {file_word} trimmed successfully!"
        print(colorama.Fore.GREEN + success_msg + colorama.Style.RESET_ALL)
    else:
        if args.file:
            clean_msg = (
                "No unused imports or dependencies found - file is already clean!"
            )
        elif args.directory:
            clean_msg = "No unused imports or dependencies found - files in directory are already clean!"
        else:
            clean_msg = (
                "No unused imports or dependencies found - project is already clean!"
            )
        print(colorama.Fore.CYAN + clean_msg + colorama.Style.RESET_ALL)

    # Check if we removed dependencies and have lock files that need regeneration
    if unused_cfg and any(unused_cfg.values()):  # If any dependencies were removed
        lock_files = detect_lock_files(args.project)
        if lock_files:
            print(f"\nLock files detected: {', '.join(lock_files)}")
            print("Consider regenerating your lock file(s) with:")
            for lock_file in lock_files:
                if lock_file == "poetry.lock":
                    print("  poetry lock")
                elif lock_file == "uv.lock":
                    print("  uv lock")
                elif lock_file == "Pipfile.lock":
                    print("  pipenv lock")
                else:
                    print(f"  # Regenerate {lock_file} with your package manager")


def find_unused_imports_in_file(file):
    """Find unused imports in a single Python file using ruff linter."""
    cmd = ["ruff", "check", file, "--select", "F401", "--output-format", "concise"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        libraries_to_process = set()
        if result.stdout.strip():
            for line in result.stdout.splitlines():
                match = re.search(r"imported but unused", line)
                if match:
                    parts = line.split()
                    if len(parts) == 7:
                        item = parts[3].removeprefix("`").removesuffix("`")
                        libraries_to_process.add(item.strip())
        return libraries_to_process
    except subprocess.CalledProcessError as e:
        sys.exit(
            colorama.Fore.RED + f"Error running ruff: {e}" + colorama.Style.RESET_ALL
        )


if __name__ == "__main__":
    main()
