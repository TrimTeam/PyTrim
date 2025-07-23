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
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and isinstance(node.value, ast.List):
                            # Store list assignments like REQUIREMENTS = [...]
                            variables[target.id] = node.value

            # Second pass: process setup() calls
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "setup":
                    for kw in n.keywords:
                        if kw.arg in ("install_requires", "extras_require", "tests_require"):
                            val = kw.value
                            
                            # Handle variable references like install_requires=REQUIREMENTS
                            if isinstance(val, ast.Name) and val.id in variables:
                                val = variables[val.id]
                            
                            if isinstance(val, ast.List):
                                out.update(self._extract_from_list(val))
                            elif isinstance(val, ast.Dict):
                                out.update(self._extract_from_dict(val))
        except SyntaxError:
            pass

        return out

    def _extract_from_list(self, val: ast.List) -> Set[str]:
        """Extract packages from an AST List node."""
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
            if isinstance(v, ast.List):
                packages.update(self._extract_from_list(v))
        return packages
