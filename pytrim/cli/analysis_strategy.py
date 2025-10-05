#!/usr/bin/env python3
"""
Analysis strategy module for managing fallback analysis methods.
"""
from pathlib import Path
import time
from enum import Enum, auto
from typing import Set, Callable, Optional
from dataclasses import dataclass
from ..utils.verbose_output import formatter
import tempfile
import os
from ..call_graph_generator import generate_cg
import colorama
import subprocess
import sys
import shutil
import re

class AnalysisMethod(Enum):
    CALL_GRAPH = auto()
    DEPTRY = auto()
    FAWLTYDEPS = auto()
    RUFF = auto()


class AnalysisResult(Enum):
    SUCCESS = auto()
    TIMEOUT = auto()
    FAILED = auto()
    NOT_AVAILABLE = auto()


@dataclass
class AnalysisOutcome:
    method: AnalysisMethod
    result: AnalysisResult
    libraries: Set[str]
    duration: float
    error_message: Optional[str] = None


@dataclass
class AnalysisStrategy:
    method: AnalysisMethod
    function: Callable
    timeout_seconds: int = 600  # fallback to other method after 10 minutes
    
    def __str__(self):
        return self.method.name.lower().replace('_', ' ')


class AnalysisChain:
    def __init__(self, strategies: list[AnalysisStrategy], verbose: bool = False):
        self.strategies = strategies
        self.verbose = verbose
    
    def execute(self, **kwargs) -> Set[str]:
        print(colorama.Fore.YELLOW + "Analyzing project dependencies..." + colorama.Style.RESET_ALL)
        """Execute strategies in order until one succeeds or all fail/timeout."""        
        for i, strategy in enumerate(self.strategies):
            try:
                start_time = time.time()
                result = self._execute_with_timeout(strategy, **kwargs)
                duration = time.time() - start_time    
                if result is not None:
                    if self.verbose:
                        formatter.success(f"{strategy} analysis completed in {duration:.1f}s")
                    return result    
            except TimeoutError as e:
                if self.verbose:
                    formatter.warning(f"{strategy} analysis timed out after {strategy.timeout_seconds}s, trying next method...")
                else:
                    print(f"{strategy} takes too much time, trying next method...")
                continue
            except Exception as e:
                if self.verbose:
                    formatter.warning(f"{strategy} analysis failed: {e}, trying next method...")
                else:
                    print(f"{strategy} failed, trying next method...")
                    print("Error details:", e)
                continue
        
        # All strategies failed
        error_msg = f"All analysis methods failed or timed out."
        raise RuntimeError(error_msg)
    
    def _execute_with_timeout(self, strategy: AnalysisStrategy, **kwargs) -> Set[str]:
        """Execute strategy with timeout handling."""
        # Prepare function arguments based on the specific strategy
        if strategy.method == AnalysisMethod.CALL_GRAPH:
            return strategy.function(
                file=kwargs.get('file'),
                directory=kwargs.get('directory'), 
                project=kwargs.get('project'),
                verbose=kwargs.get('verbose', False),
                timeout=strategy.timeout_seconds
            )
        elif strategy.method == AnalysisMethod.DEPTRY:
            return strategy.function(
                project=kwargs.get('project', '.'),
                timeout=strategy.timeout_seconds
            )
        elif strategy.method == AnalysisMethod.FAWLTYDEPS:
            return strategy.function(
                deps=kwargs.get('cfg_files'),
                project=kwargs.get('project', '.'),
                timeout=strategy.timeout_seconds
            )
        else:
            # Fallback: call with all kwargs
            return strategy.function(**kwargs)


def create_analysis_chain(args) -> AnalysisChain:
    """Create analysis chain based on user preferences and fallbacks."""
    strategies = []
    
    if args.deptry:
        
        strategies = [AnalysisStrategy(
            AnalysisMethod.DEPTRY, 
            find_unused_imports_with_deptry,
        ),
        AnalysisStrategy(
            AnalysisMethod.CALL_GRAPH, 
            find_unused_imports_with_cg_analysis
        ),
        AnalysisStrategy(
            AnalysisMethod.FAWLTYDEPS, 
            find_unused_deps_with_fawltydeps,
        )]
        
    elif args.fawltydeps:
        
        strategies = [AnalysisStrategy(
            AnalysisMethod.FAWLTYDEPS, 
            find_unused_deps_with_fawltydeps,    
        ),
        AnalysisStrategy(
            AnalysisMethod.CALL_GRAPH, 
            find_unused_imports_with_cg_analysis
        ),
        AnalysisStrategy(
            AnalysisMethod.DEPTRY, 
            find_unused_imports_with_deptry,
        )]
        
    else:
        strategies = [AnalysisStrategy(
            AnalysisMethod.CALL_GRAPH, 
            find_unused_imports_with_cg_analysis
        ),
        AnalysisStrategy(
            AnalysisMethod.FAWLTYDEPS, 
            find_unused_deps_with_fawltydeps
        ),
        AnalysisStrategy(
            AnalysisMethod.DEPTRY, 
            find_unused_imports_with_deptry
        )]   
    return AnalysisChain(strategies, verbose=args.verbose)

def find_unused_imports_with_cg_analysis(file, directory, project, timeout, verbose=False):
    if not file and not directory:
        try:
            libraries_to_process = generate_cg.find_unused_deps_with_cg(project, timeout=timeout)
        except TimeoutError as e:
            raise TimeoutError("Call graph generation timed out")
        project_root = Path(project)
        # Clean up temporary files
        if verbose:
            formatter.info("Cleaning up temporary files...")
            tmp_dirs = [project_root / "tmp1", project_root / "call_graph_data"]
            for tmp_dir in tmp_dirs:
                if tmp_dir.exists():
                    shutil.rmtree(tmp_dir)
        else:
            tmp_dirs = [project_root / "tmp1", project_root / "call_graph_data"]
            for tmp_dir in tmp_dirs:
                if tmp_dir.exists():
                    shutil.rmtree(tmp_dir)

        return libraries_to_process
    else:
        libraries_to_process = set()
    return libraries_to_process


def find_unused_deps_with_fawltydeps(deps: str, timeout: int,  project :str =".", ):
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
            sys.exit(colorama.Fore.RED + "No valid dependency files found for fawltydeps processing." + colorama.Style.RESET_ALL)
        cmd = ["fawltydeps", project, "--check-unused", "--install-deps"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        libraries_to_process = set()
        if result.stdout.strip():
            for line in result.stdout.splitlines():
                if line.startswith("-"):
                    libraries_to_process.add(
                        line.strip().split(" ")[1].removeprefix("'").removesuffix("'")
                    )
        return libraries_to_process
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Fawltydeps analysis timed out after {timeout} seconds")
    except Exception as e:
        return Exception("Error running fawltydeps")


def find_unused_imports_with_deptry(timeout, project="."):
    """Find unused imports using deptry."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = os.path.join(temp_dir, "deptry_venv")
            subprocess.run([sys.executable, "-m", "venv", venv_path], check=True, capture_output=True)
            if sys.platform.startswith("win"):
                venv_python = os.path.join(venv_path, "Scripts", "python.exe")
            else:
                venv_python = os.path.join(venv_path, "bin", "python")
            subprocess.run([venv_python, "-m", "pip", "install", "deptry"], check=True, capture_output=True)
            subprocess.run([venv_python, "-m", "pip", "install", project], check=True, capture_output=True, timeout=timeout//2)

            cmd = [venv_python, "-m", "deptry", ".", "--ignore", "DEP001,DEP003,DEP004"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=os.path.abspath(project), timeout=timeout//2
            )

            libraries_to_process = set()
            if result.stderr.strip():
                for line in result.stderr.splitlines():
                    if "DEP002" in line:
                        libraries_to_process.add(
                            line.strip()
                            .split(" ")[2]
                            .removeprefix("'")
                            .removesuffix("'")
                        )
        return libraries_to_process
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Deptry analysis timed out after {timeout} seconds")
    except subprocess.CalledProcessError as e:
        sys.exit(colorama.Fore.RED + f"Error running deptry: {e}" + colorama.Style.RESET_ALL)