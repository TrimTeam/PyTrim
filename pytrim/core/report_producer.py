import ast
from collections import defaultdict
from pathlib import Path


def create_report(data: dict, fname: str) -> None:
    out = [
        f"**File:**  ``{fname}``",
        "",
        "| Module | Name | Alias | Line |",
        "|--------|------|-------|------|",
    ]
    total = 0
    for mod, items in data.items():
        for i in items:
            alias = i["alias"] or "None"
            out.append(f"| {mod} | {i['name']} | {alias} | {i['line']} |")
            total += 1
    out += ["", f"**Total unused imports: {total}**"]
    rpt = Path("reports")
    rpt.mkdir(exist_ok=True)
    (rpt / f"{Path(fname).stem}-report.md").write_text("\n".join(out))


def create_unused_imports_dict(unused: set, tree: ast.AST) -> dict:
    d = defaultdict(list)
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name in unused:
                    d[a.name].append(
                        {"name": a.name, "alias": a.asname, "line": a.lineno}
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            for a in node.names:
                if root in unused or a.name in unused or (a.asname or "") in unused:
                    d[node.module].append(
                        {"name": a.name, "alias": a.asname, "line": a.lineno}
                    )
    return d


def create_dir_report(rdir: str) -> None:
    rpt = Path(rdir)
    rpt.mkdir(exist_ok=True)
    content = []
    for f in rpt.glob("*.md"):
        content.append(f.read_text())
        content.append("\n---\n")
        f.unlink()
    (rpt / "folder_report.md").write_text("".join(content))


def create_config_report(data: dict, fname: str) -> None:
    """Create individual report for config file dependencies."""
    out = [
        f"**File:**  ``{fname}``",
        "",
        "| Package | Status |",
        "|---------|--------|",
    ]
    total = 0
    for dep in sorted(data):
        out.append(f"| {dep} | Removed |")
        total += 1
    out += ["", f"**Total unused dependencies: {total}**"]
    rpt = Path("reports")
    rpt.mkdir(exist_ok=True)
    (rpt / f"{Path(fname).stem}-config-report.md").write_text("\n".join(out))


def create_comprehensive_summary(folder_content: str, unused_cfg: dict) -> str:
    """Create comprehensive summary of all changes (Python + config files)."""
    summary_lines = ["## Summary of All Changes", ""]

    total_python_imports = 0
    total_config_deps = 0
    files_with_config_changes = 0

    # Count Python imports removed from the folder content
    lines = folder_content.split("\n")
    for line in lines:
        if "**Total unused imports:" in line:
            try:
                count = int(line.split(":")[1].strip().rstrip("**"))
                total_python_imports += count
            except (IndexError, ValueError):
                pass

    # Count config dependencies removed and files changed
    for cfg, deps in unused_cfg.items():
        if deps:
            total_config_deps += len(deps)
            files_with_config_changes += 1

    if total_python_imports > 0:
        summary_lines.append(
            f"- **Python Files:** Removed {total_python_imports} unused import(s)"
        )

    if total_config_deps > 0:
        if files_with_config_changes == 1:
            summary_lines.append(
                f"- **Config Files:** Removed {total_config_deps} unused dependency/ies from {files_with_config_changes} file"
            )
        else:
            summary_lines.append(
                f"- **Config Files:** Removed {total_config_deps} unused dependency/ies from {files_with_config_changes} files"
            )

    if total_python_imports == 0 and total_config_deps == 0:
        summary_lines.append("**No unused imports or dependencies found.**")

    summary_lines.extend(["", "---", ""])

    return "\n".join(summary_lines)


def create_project_report(rdir: str, unused_cfg: dict) -> None:
    report_path = Path(rdir) / "project_report.md"
    # if the file exists, clear it
    if report_path.exists():
        report_path.write_text("")
    create_dir_report(rdir)
    folder = Path(rdir) / "folder_report.md"
    txt = folder.read_text()

    lines = [txt, "## Config Files Changed", ""]
    filtered = {cfg: deps for cfg, deps in unused_cfg.items() if deps}
    if not filtered:
        lines.append("**No config files changed.**")
    else:
        for cfg, deps in filtered.items():
            cfg_name = Path(cfg).name
            lines.append(f"**{cfg_name}:** {sorted(deps)}")
            lines.append("")

    # Add comprehensive summary at the end
    summary = create_comprehensive_summary(txt, unused_cfg)
    lines.extend(["", summary])

    report_path.write_text("\n".join(lines))
    folder.unlink()
