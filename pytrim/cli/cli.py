import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from importlib import metadata
from pathlib import Path
import re
from ..call_graph_generator import generate_cg
from ..extractors.dependency_extractor import extract_deps
import colorama 
from ..analyzers.module_analyzer import ensure_mappings, get_correct_names
from tqdm import tqdm
import os
import tempfile
from ..analyzers.dependency_analyzer import (
    find_unused_direct_dependencies,
)
from ..core import file_remover
from ..core.report_producer import create_dir_report, create_project_report
from ..removers.config_file_remover import remove_unused_dependencies
from ..utils.file_patterns import discover_config_files, discover_python_files


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
    if (path / "bin" / "activate").exists() or (path / "Scripts" / "activate.bat").exists():
        return True
    
    # Check for site-packages directory structure
    lib_dir = path / "lib"
    if lib_dir.exists():
        for subdir in lib_dir.iterdir():
            if subdir.is_dir() and subdir.name.startswith("python") and (subdir / "site-packages").exists():
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
        'test', 'tests', 'testing', '__pycache__',
        'tmp', 'temp', '.git', '.cache', '.pytest_cache',
        'build', 'dist', '.tox', '.coverage',
        '.idea', '.vscode', '.mypy_cache', 'node_modules',
        '.github', '.gitlab', '.circleci', '.travis',
        'site-packages', 'egg-info'
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
        builtin_mappings = package_dir / "import_mappings.json"
        if builtin_mappings.exists():
            if args.verbose:
                print(f"Using built-in import mappings")
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


def main():
    parser = argparse.ArgumentParser(
        description="Trim unused Python imports and dependencies. Run 'trim' or 'pytrim' in your project directory to get started.",
        formatter_class=CustomHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--file", help="Single Python file to trim.")
    group.add_argument("-d", "--directory", help="Directory of Python files to trim.")
    group2 = parser.add_mutually_exclusive_group()
    parser.add_argument(
        "project",
        nargs="?",
        default=".",
        help="Project path to trim (default: current directory). Use 'trim' with no args to trim current project.",
    )
    parser.add_argument(
        "-u",
        "--unused-imports",
        nargs="+",
        help="Specific packages to remove (optional - auto-detects if not specified)."
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
        help="Create new debloated files (to 'output/') instead of overwriting originals.",
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
    group2.add_argument(
        "-cg",
        "--call-graph",
        action="store_true",
        help="Use call graph analysis to find unused imports (requires call_graph_generator installed).",
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
        "--generate-mappings",
        nargs="*",
        help="Generate import mappings JSON file for specified packages (or use discovered packages if none specified).",
    )
    parser.add_argument(
        "--mappings-file",
        help="Use custom import mappings JSON file instead of built-in mappings.",
    )
    parser.add_argument(
        "-e", "--exclude",nargs="+", 
        help="Exclude specific dependencies from the removal process." \
        "E.g. a transitive dependency that needs its version pinned."
    )
    args = parser.parse_args()
    root = Path(args.project)
    packages = set()
    # Handle mapping generation
    if args.generate_mappings is not None:
        from pytrim.utils.generate_import_mappings import (
            generate_mappings_from_packages,
        )       
        if args.generate_mappings:
            packages = args.generate_mappings
        else:  
            py_files = discover_python_files(root)
            cfg_files = discover_config_files(root)      
            for cfg in cfg_files:
                packages.update(extract_deps(Path(cfg)))
            packages = list(packages)

            if args.verbose:
                print(
                    f"Discovered {len(packages)} packages from project: {packages[:10]}..."
                )
        output_file = "import_mappings.json"
        print(f"Generating import mappings for {len(packages)} packages...")
        generate_mappings_from_packages(packages, output_file, args.verbose)
        print(f"✓ Import mappings saved to {output_file}")
        return
    else:
        cfg_files = discover_config_files(root)
        for cfg in cfg_files:
            packages = extract_deps(Path(cfg))
    if args.unused_imports:
        # User provided specific packages
        libraries_to_process = set(args.unused_imports)
    elif args.deptry:
        libraries_to_process = find_unused_imports_with_deptry(args.project)
    elif args.fawltydeps:
        root = Path(args.project)
        cfg_files = discover_config_files(root)
        libraries_to_process = find_unused_deps_with_fawltydeps(cfg_files, args.project)
    else:
        libraries_to_process = find_unused_imports_with_cg_analysis(
            args.file, args.directory, args.project, args.verbose, cfg_files
        )
    if "" in libraries_to_process:
        libraries_to_process.remove("")
    colorama.init(autoreset=True)
    if args.exclude:
        libraries_to_process.remove(*args.exclude)
    
    # Process libraries: check mappings and generate missing ones
    if libraries_to_process:
        print(colorama.Fore.RED+ f"\nFound unused dependencies: {libraries_to_process}")
        root = Path(args.project)
        mappings_file = _get_mappings_file(args, root)


        mappings = ensure_mappings(libraries_to_process, mappings_file, args.verbose)
        # Get correct names for Python files (import names)
        unused = get_correct_names(libraries_to_process, mappings, file_type="python")

        if args.verbose:
            print(f"Libraries to process: {sorted(libraries_to_process)}")
            print(f"Import names for Python files: {sorted(unused)}")
    else:
        sys.exit(colorama.Fore.GREEN + "\nNo unused dependencies found. You can try another unused imports detection method.")

    # Discover files
    if args.file:
        py_files, cfg_files = [Path(args.file)], []
    elif args.directory:
        py_files, cfg_files = list(Path(args.directory).glob("*.py")), []
    else:
        root = Path(args.project)
        py_files = discover_python_files(root)
        all_cfg_files = discover_config_files(root)
        # Filter out config files from test and temporary directories
        cfg_files = [f for f in all_cfg_files if not _is_in_excluded_directory(f, root)]
        if args.verbose:
            print(f"\nDiscovered {len(all_cfg_files)} config files total")
            print(f"Processing {len(cfg_files)} config files (excluding test/temp directories):")
            for f in cfg_files:
                print(f"  {f.relative_to(root)}")

    # Process Python files
    with tqdm(desc="Processing Python files", ncols=80, colour="green") as pbar:
        files_modified = 0
        for p in py_files:
            # Check if file has unused imports before processing
            try:
                code = p.read_text(encoding="utf-8")
                tree = file_remover.ast.parse(code)
                if file_remover.file_contains_unused_imports(tree, unused):
                    if args.verbose:
                        print(f"\nProcessing {p} - has unused imports")
                    files_modified += 1
                file_remover.debloat_file(
                    str(p), unused, args.verbose, args.report, args.output
                )
            except Exception as e:
                if args.verbose:
                    print(f"\nSkipping {p}: {e}")
        if args.verbose:
            print(f"\nModified {files_modified} Python files")
        pbar.update(100)

    # Process config files (project mode only)
    if not args.file and not args.directory:
        with tqdm(desc="Updating config files", ncols=80, colour="green") as pbar:
            root = Path(args.project)

            mappings_file = _get_mappings_file(args, root)

            if libraries_to_process:
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
                    print(
                        f"Removing packages from config files: {sorted(unused_cfg_packages)}"
                    )
            else:
                ensure_mappings(unused, mappings_file, args.verbose)

                unused_cfg = find_unused_direct_dependencies(
                    [str(p) for p in py_files],
                    [str(p) for p in cfg_files],
                    str(root),
                    unused,
                    mappings_file,
                    libraries_to_process,
                )

            remove_unused_dependencies([str(p) for p in cfg_files], unused_cfg, args.output)

            # Filter unused_cfg to only include files that were actually processed
            processed_files = {str(p) for p in cfg_files}
            if args.verbose:
                print(
                    f"\nProcessed config files: {[Path(p).name for p in processed_files]}"
                )
                print(
                    f"Unused_cfg before filtering: {[(Path(k).name, v) for k, v in unused_cfg.items()]}"
                )
            unused_cfg = {k: v for k, v in unused_cfg.items() if k in processed_files}
            if args.verbose:
                print(
                    f"Unused_cfg after filtering: {[(Path(k).name, v) for k, v in unused_cfg.items()]}"
                )

            pbar.update(100)
    else:
        unused_cfg = {}

    # Generate reports if requested
    if args.report:
        with tqdm(desc="Generating reports", ncols=80, colour="green") as pbar:
            if args.directory:
                create_dir_report("reports")
            if not args.file and not args.directory:
                create_project_report("reports", unused_cfg)
            pbar.update(100)

        if not args.file and not args.directory and args.pull_request:
            root = Path(args.project)
            rpt_dir = root / "reports"
            pr_file = rpt_dir / "project_report.md"
            dest = root / "project_report.md"
            pr_file.replace(dest)
            shutil.rmtree(rpt_dir)

            repo = root
            branch = f"debloat/{datetime.now().strftime('%Y%m%d%H%M%S')}"
            if not (repo / ".git").exists():
                print(f"Error: {repo} is not a git repository.")
                sys.exit(1)
            if not shutil.which("git") or not shutil.which("gh"):
                print("Error: 'git' and 'gh' CLI required for PR creation")
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
                print(f"Error: {e}")
                sys.exit(1)

    print(
        "\n✓ Project trimmed successfully!"
        if not (args.file or args.directory)
        else "✓ Files processed successfully!"
    )

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


def find_unused_imports_with_cg_analysis(file, directory, project, verbose, cfg_files):
    if not file and not directory:
        # Generate call graphs
        with tqdm(desc="Generating call graph", ncols=80, colour="green") as pbar:
            libraries_to_process = generate_cg.find_unused_deps_with_cg(project)
            pbar.update(200)
        project_root = Path(project)
        # Clean up temporary files
        with tqdm(desc="Cleaning up temporary files", ncols=80, colour="green") as pbar:
            tmp_dirs = [project_root / "tmp1", project_root / "call_graph_data"]
            for tmp_dir in tmp_dirs:
                if tmp_dir.exists():
                    shutil.rmtree(tmp_dir)
            pbar.update(100)
        return libraries_to_process
    else:
        libraries_to_process = set()
    return libraries_to_process


def find_unused_deps_with_fawltydeps(deps:str, project="."):
    """Find unused dependencies using fawltydeps.
    Fawltydeps supports the following files:
    * requirements.txt and requirements.in
    * pyproject.toml (following PEP 621 or Poetry conventions)
    * setup.py (only limited support for simple files with a single setup() call and no computation involved for setting the install_requires and extras_require arguments)
    * setup.cfg
    * pixi.toml
    * environment.yml
    """
    try:
        pattern = re.compile(r".*\.(txt|in|cfg|toml|py|yml)$", re.I)
        filtered = [str(dep) for dep in deps if pattern.match(str(dep))]
        if not filtered:
            sys.exit("No valid dependency files found for fawltydeps processing.")
        cmd = ["fawltydeps", project, "--check-unused", "--install-deps"]
        result = subprocess.run(
            cmd, capture_output=True, text=True
        )
        libraries_to_process = set()
        if result.stdout.strip():
            for line in result.stdout.splitlines():
                if line.startswith("-"):
                    libraries_to_process.add(
                        line.strip().split(" ")[1].removeprefix("'").removesuffix("'")
                    )
        return libraries_to_process
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error running fawltydeps: {e}")


def find_unused_imports_with_deptry(project="."):
    """Find unused imports using deptry."""
    try:        
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = os.path.join(temp_dir, "deptry_venv")
            subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
            if sys.platform.startswith("win"):
                venv_python = os.path.join(venv_path, "Scripts", "python.exe")
            else:
                venv_python = os.path.join(venv_path, "bin", "python")
            subprocess.run([venv_python, "-m", "pip", "install", "deptry"], check=True)
            subprocess.run([venv_python, "-m", "pip", "install", project], check=True)
            
            cmd = [venv_python, "-m", "deptry", ".", "--ignore", "DEP001,DEP003,DEP004"]
            result = subprocess.run(cmd, capture_output=True, text=True , cwd=os.path.abspath(project))

            libraries_to_process = set()
            if result.stderr.strip():
                for line in result.stderr.splitlines():
                    if "DEP002" in line:
                        libraries_to_process.add(
                            line.strip().split(" ")[2].removeprefix("'").removesuffix("'")
                        )        
        return libraries_to_process       
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error running deptry: {e}")


if __name__ == "__main__":
    main()
