#!/usr/bin/env python3
"""
Orchestrator module that runs all call-graph generation steps
"""
import os
import subprocess
import sys
from shutil import which
from .find_direct_and_unused_deps import get_unused_deps
from ..analyzers.module_analyzer import ensure_mappings
import json

def run_step(cmd, step_name):
    """
    Execute a subprocess command and handle errors.
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error in {step_name}:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)


def run_all(dest_dir: str):
    """
    Execute all call-graph steps in order via subprocess:
      1) dependency resolution
      2) project partial CG
      3) dependency partial CG
      4) stitch CGs
    """
    dest_dir = os.path.abspath(dest_dir)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1) Resolve dependencies
    run_step(
        [
            sys.executable,
            os.path.join(base_dir, "dependency_resolution", "dependency_resolver.py"),
            "--directory",
            dest_dir,
        ],
        "dependency resolution",
    )

    # 2) if pycg is not installed, we need to install it
    if which("pycg") is None:
        print("PyCG is not installed. Install it with:")
        print(
            "git clone https://github.com/gdrosos/PyCG.git\n"
            "cd PyCG\n"
            "pip3 install .\n"
            'export PATH="$HOME/.local/bin:$PATH"'
    )
        sys.exit(1)

    # 3) find top_level names of each dep
    resolved_json = os.path.join(
        dest_dir, "call_graph_data", "resolved_dependencies.json"
    )
    deps = find_packages_without_version(resolved_json)
    mappings_file = os.path.join("pytrim", "import_mappings.json")
    mappings = ensure_mappings(deps, mappings_file)
    # 4) Produce project partial call graph
    run_step(
        [
            sys.executable,
            os.path.join(
                base_dir, "partial_cg_generation", "produce_project_partial_cg.py"
            ),
            "--source",
            dest_dir,
        ],
        "project partial CG",
    )
    # 5) Find unused direct dependencies
    cg_path = os.path.join(dest_dir, "call_graph_data", "cg.json")
    unused_direct_deps = get_unused_deps(cg_path, mappings)
    return unused_direct_deps


def find_unused_deps_with_cg(dest_dir: str):
    try:
        unused_direct_deps = run_all(dest_dir)
        return unused_direct_deps
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

def find_packages_without_version(resolved_json):
    if not os.path.exists(resolved_json):
        print(f"Resolved dependencies file {resolved_json} does not exist.")
        return
    with open(resolved_json, 'r') as f:
        resolved_deps = json.load(f)
    deps = [dep.split(":")[0] for dep in resolved_deps[resolved_json.split("/")[-3]]]
    return deps