"""Python files (setup.py) dependency extractor."""

import ast
from pathlib import Path
from typing import Set

from ..utils.package_utils import normalize
from .base import BaseExtractor


class PythonFileExtractor(BaseExtractor):
    """Extractor for Python files like setup.py."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this is a Python file we can handle."""
        return file_path.suffix == ".py" and file_path.name == "setup.py"

    def extract(self, file_path: Path, seen: Set[Path] = None) -> Set[str]:
        """Extract dependencies from setup.py files."""
        if seen is None:
            seen = set()
        if file_path in seen:
            return set()
        seen.add(file_path)

        if not file_path.is_file():
            return set()

        text = self.read_file_safely(file_path)
        if not text:
            return set()

        out = set()

        try:
            tree = ast.parse(text)
            
            # First pass: collect variable assignments
            variables = {}
            dict_variables = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if isinstance(node.value, (ast.List, ast.Tuple)):
                                # Store list/tuple assignments like REQUIREMENTS = [...] or REQUIREMENTS = (...)
                                variables[target.id] = node.value
                            elif isinstance(node.value, ast.Dict):
                                # Store dict assignments like config = {...}
                                dict_variables[target.id] = node.value

            # Second pass: process setup() calls
            for n in ast.walk(tree):
                is_setup_call = False
                if isinstance(n, ast.Call):
                    # Handle both setup() and setuptools.setup()
                    if isinstance(n.func, ast.Name) and n.func.id == "setup":
                        is_setup_call = True
                    elif isinstance(n.func, ast.Attribute) and n.func.attr == "setup":
                        is_setup_call = True
                
                if is_setup_call:
                    # Handle direct keyword arguments
                    for kw in n.keywords:
                        if kw.arg in ("install_requires", "extras_require", "tests_require"):
                            val = kw.value
                            
                            # Handle variable references like install_requires=REQUIREMENTS
                            if isinstance(val, ast.Name) and val.id in variables:
                                val = variables[val.id]
                            
                            if isinstance(val, (ast.List, ast.Tuple)):
                                out.update(self._extract_from_list(val))
                            elif isinstance(val, ast.Dict):
                                out.update(self._extract_from_dict(val))
                    
                    # Handle dictionary unpacking like setup(**config)
                    for starred in n.keywords:
                        if starred.arg is None:  # This indicates **kwargs unpacking
                            if isinstance(starred.value, ast.Name) and starred.value.id in dict_variables:
                                config_dict = dict_variables[starred.value.id]
                                out.update(self._extract_from_config_dict(config_dict))
        except SyntaxError:
            pass

        return out

    def _extract_from_list(self, val) -> Set[str]:
        """Extract packages from an AST List or Tuple node."""
        packages = set()
        for e in val.elts:
            pkg_str = None
            if isinstance(e, ast.Constant):
                pkg_str = e.value if hasattr(e, "value") else e.s
            elif isinstance(e, ast.Str):
                pkg_str = e.s
            
            if pkg_str:
                pkg = normalize(
                    str(pkg_str)
                    .split("==")[0]
                    .split(">=")[0]
                    .split("<=")[0]
                    .split(">")[0]
                    .split("<")[0]
                    .split("!")[0]
                    .split("~=")[0]
                    .split(";")[0]
                )
                packages.add(pkg)
        return packages

    def _extract_from_dict(self, val: ast.Dict) -> Set[str]:
        """Extract packages from an AST Dict node (for extras_require)."""
        packages = set()
        for v in val.values:
            if isinstance(v, (ast.List, ast.Tuple)):
                packages.update(self._extract_from_list(v))
        return packages

    def _extract_from_config_dict(self, config_dict: ast.Dict) -> Set[str]:
        """Extract packages from a config dictionary like config = {'install_requires': [...]}."""
        packages = set()
        for key, value in zip(config_dict.keys, config_dict.values):
            # Check if this is a dependency-related key
            if isinstance(key, (ast.Str, ast.Constant)):
                key_name = key.s if isinstance(key, ast.Str) else key.value
                if key_name in ("install_requires", "extras_require", "tests_require"):
                    if isinstance(value, (ast.List, ast.Tuple)):
                        packages.update(self._extract_from_list(value))
                    elif isinstance(value, ast.Dict):
                        packages.update(self._extract_from_dict(value))
        return packages
