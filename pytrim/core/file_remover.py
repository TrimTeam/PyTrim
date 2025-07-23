import ast
from pathlib import Path

from . import report_producer


def file_contains_unused_imports(tree: ast.Module, unused: set) -> bool:
    """Check if the file contains any of the unused imports before processing."""
    for node in ast.walk(tree):  # Use ast.walk to check all nodes, not just top-level
        if isinstance(node, ast.Import):
            for a in node.names:
                name = a.name
                alias = a.asname or name
                if name in unused or alias in unused or name.split(".")[0] in unused:
                    return True
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in unused or node.module in unused:
                return True
            for a in node.names:
                name = a.name
                alias = a.asname or name
                if name in unused or alias in unused or name.split(".")[0] in unused:
                    return True
        # Check for dynamic imports
        elif isinstance(node, ast.Assign):
            for value in ast.walk(node):
                if isinstance(value, ast.Call):
                    try:
                        if isinstance(value.func, ast.Attribute):
                            # Handle `importlib.import_module`
                            if (
                                hasattr(value.func.value, "id")
                                and value.func.value.id == "importlib"
                                and hasattr(value.func, "attr")
                                and value.func.attr == "import_module"
                                and value.args
                                and hasattr(value.args[0], "s")
                                and value.args[0].s in unused
                            ):
                                return True
                        elif isinstance(value.func, ast.Name):
                            # Handle `__import__`
                            if (
                                value.func.id == "__import__"
                                and value.args
                                and hasattr(value.args[0], "s")
                                and value.args[0].s in unused
                            ):
                                return True
                    except (AttributeError, IndexError):
                        # Skip malformed nodes
                        continue
    return False


def get_import_lines(tree: ast.Module) -> set:
    """Get all line numbers that contain import statements."""
    import_lines = set()
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                for line in range(node.lineno, node.end_lineno + 1):
                    import_lines.add(line)
            elif hasattr(node, "lineno"):
                import_lines.add(node.lineno)
    return import_lines


def _is_import_unused(import_name: str, alias: str, unused: set) -> bool:
    """Helper function to check if an import is unused."""
    return (
        import_name in unused or alias in unused or import_name.split(".")[0] in unused
    )


def remove_unused_imports_from_code(code: str, tree: ast.Module, unused: set) -> str:
    """Remove unused imports while keeping the rest of the code intact."""
    lines = code.splitlines(keepends=True)
    removed_lines = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            all_unused = all(
                _is_import_unused(a.name, a.asname or a.name, unused)
                for a in node.names
            )
            if all_unused:
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    for line in range(node.lineno, node.end_lineno + 1):
                        removed_lines.add(line)
                elif hasattr(node, "lineno"):
                    removed_lines.add(node.lineno)
            elif any(
                _is_import_unused(a.name, a.asname or a.name, unused)
                for a in node.names
            ):
                kept_names = [
                    a
                    for a in node.names
                    if not _is_import_unused(a.name, a.asname or a.name, unused)
                ]
                if kept_names and hasattr(node, "lineno"):
                    new_import = (
                        f"import {', '.join(a.asname or a.name for a in kept_names)}\n"
                    )
                    lines[node.lineno - 1] = new_import

        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in unused or node.module in unused:
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    for line in range(node.lineno, node.end_lineno + 1):
                        removed_lines.add(line)
                elif hasattr(node, "lineno"):
                    removed_lines.add(node.lineno)
            else:
                kept_names = [
                    a
                    for a in node.names
                    if not _is_import_unused(a.name, a.asname or a.name, unused)
                ]
                if (
                    kept_names
                    and len(kept_names) < len(node.names)
                    and hasattr(node, "lineno")
                ):
                    names_str = ", ".join(
                        f"{a.name} as {a.asname}" if a.asname else a.name
                        for a in kept_names
                    )
                    new_import = f"from {node.module} import {names_str}\n"
                    lines[node.lineno - 1] = new_import
                elif not kept_names and hasattr(node, "lineno"):
                    removed_lines.add(node.lineno)

        # Check for dynamic imports
        elif isinstance(node, ast.Assign):
            for value in ast.walk(node):
                if isinstance(value, ast.Call):
                    try:
                        if isinstance(value.func, ast.Attribute):
                            # Handle `importlib.import_module`
                            if (
                                hasattr(value.func.value, "id")
                                and value.func.value.id == "importlib"
                                and hasattr(value.func, "attr")
                                and value.func.attr == "import_module"
                                and value.args
                                and hasattr(value.args[0], "s")
                                and value.args[0].s in unused
                            ):
                                removed_lines.add(node.lineno)
                        elif isinstance(value.func, ast.Name):
                            # Handle `__import__`
                            if (
                                value.func.id == "__import__"
                                and value.args
                                and hasattr(value.args[0], "s")
                                and value.args[0].s in unused
                            ):
                                removed_lines.add(node.lineno)
                    except (AttributeError, IndexError):
                        # Skip malformed nodes
                        continue

    return return_new_code(lines, removed_lines)


def return_new_code(lines: list[str], removed_lines: set[int]) -> str:
    """Return the code with specified lines removed."""
    result_lines = []
    for i, line in enumerate(lines, 1):
        if i not in removed_lines:
            result_lines.append(line)
    return "".join(result_lines)


def debloat_file(
    path: str,
    unused_imports: set,
    verbose: bool = False,
    report: bool = False,
    create_debloated: bool = False,
) -> None:
    """Remove unused imports from a Python file."""
    p = Path(path)

    # Check if the file is a Python file
    if p.suffix.lower() != ".py":
        if verbose:
            print(f"Skipping {path}: not a Python file")
        return

    # Read file with encoding fallback
    try:
        code = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            code = p.read_text(encoding="latin-1")
        except UnicodeDecodeError:
            if verbose:
                print(f"Warning: cannot decode {path}: unsupported encoding")
            return

    # Parse AST
    try:
        tree = ast.parse(code)
    except (SyntaxError, TabError) as e:
        if verbose:
            print(f"Warning: cannot parse {path}: {e}")
        return

    unused_imports = set(unused_imports)

    # Check if file contains any unused imports before processing
    if not file_contains_unused_imports(tree, unused_imports):
        if verbose:
            print(f"Skipping {path}: no unused imports found")
        return

    if report:
        pre = report_producer.create_unused_imports_dict(unused_imports, tree)

    out_code = remove_unused_imports_from_code(code, tree, unused_imports)

    if report:
        report_producer.create_report(pre, p.name)

    # Write output
    if create_debloated:
        # Create debloated files in output directory
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        (out_dir / f"{p.stem}_debloated.py").write_text(out_code, encoding="utf-8")
    else:
        # Overwrite original file
        p.write_text(out_code, encoding="utf-8")
