#!/usr/bin/env python3
"""
Orchestrator module that runs all call-graph generation steps
"""
import os
import subprocess
import sys
from shutil import which
from .find_direct_and_unused_deps import get_unused_deps


def run_step(cmd, step_name, timeout):
    """
    Execute a subprocess command and handle errors.
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=timeout)
    except subprocess.CalledProcessError as e:
        print(f"Error in {step_name}:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        raise TimeoutError()


def run_all(dest_dir: str, timeout: int):
    """
    Execute all call-graph steps in order via subprocess:
      1) dependency resolution
      2) project partial CG
      3) dependency partial CG
      4) stitch CGs
    """
    dest_dir = os.path.abspath(dest_dir)
    base_dir = os.path.dirname(os.path.abspath(__file__))


    # 1) if pycg is not installed, we need to install it
    if which("pycg") is None:
        print("PyCG is not installed. Install it with:")
        print(
            "git clone https://github.com/gdrosos/PyCG.git\n"
            "cd PyCG\n"
            "pip3 install .\n"
            'export PATH="$HOME/.local/bin:$PATH"'
    )
        sys.exit(1)

    # 2) Produce project partial call graph
    try:
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
            timeout=timeout,
        )
    except TimeoutError:
        raise TimeoutError()
    # 3) Find unused direct dependencies with dynamic and static dependency resolution and call graph parsing
    cg_path = os.path.join(dest_dir, "call_graph_data", "cg.json")
    unused_direct_deps = get_unused_deps(cg_path, dest_dir)
    return unused_direct_deps


def find_unused_deps_with_cg(dest_dir: str, timeout: int):
    try:
        unused_direct_deps = run_all(dest_dir, timeout=timeout)
        return unused_direct_deps
    except TimeoutError:
        raise TimeoutError
    except Exception as e:
        raise Exception