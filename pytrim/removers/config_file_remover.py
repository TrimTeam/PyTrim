"""Main config file remover that coordinates all handler types."""

from pathlib import Path
from typing import Dict, List, Set

from .base import BaseRemover
from .handlers import (
    GeneralConfigRemover,
    IniFilesRemover,
    RequirementsRemover,
    SystemFilesRemover,
    YamlRemover,
)


class ConfigFileRemover:
    """Main config file remover that coordinates all handler types."""

    def __init__(self):
        self.removers: List[BaseRemover] = [
            RequirementsRemover(),
            YamlRemover(),
            SystemFilesRemover(),
            IniFilesRemover(),  # Handle .ini files before general config
            GeneralConfigRemover(),  # Keep this last as it's the most general
        ]

    def remove_unused_dependencies(
        self, cfg_files: List[str], unused_map: Dict[str, Set[str]], create_debloated: bool = False
    ) -> None:
        """Remove unused dependencies from config files."""
        # .in files must be handled before .txt files (.in files are input for pip-compile)
        cfg_files = sorted(cfg_files, key=lambda x: (x.endswith(".in"), x))
        cfg_files.reverse()
        for cfg in cfg_files:
            unused = unused_map.get(cfg, set())
            if not unused:
                continue

            p = Path(cfg)
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            lines = text.split("\n")
            # Find the appropriate remover for this file
            remover = self._find_remover(p)
            if remover:
                # if pip-compile is used, then out is None because we are not storing anything
                out = remover.remove_unused(p, unused, lines)
            else:
                # No specific remover found, keep original content
                out = lines

            # Handle the case where out is None (used by pip-compile)
            if out is None:
                continue
            new_content = "\n".join(out)

            if lines != out:
                if create_debloated:
                    out_dir = Path("output")
                    out_dir.mkdir(exist_ok=True)
                    (out_dir / f"{p.stem}_debloated.{p.suffix}").write_text(new_content, encoding="utf-8")
                else:
                    # For .in files, the RequirementsRemover handles writing both .in and .txt files
                    if p.suffix != ".in":
                        p.write_text(new_content, encoding="utf-8")

    def _find_remover(self, file_path: Path) -> BaseRemover:
        """Find the appropriate remover for this file."""
        for remover in self.removers:
            if remover.can_handle(file_path):
                return remover
        return None

    def _write_to_output_dir(self, original_path: Path, content: str) -> None:
        """Write debloated content to output directory."""
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)

        if original_path.is_dir():
            dest = out_dir / f"{original_path.name}_debloated"
            dest.mkdir(exist_ok=True)
            for file in original_path.rglob("*"):
                if file.is_file():
                    rel_path = file.relative_to(original_path)
                    dest_file = dest / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    dest_file.write_text(
                        file.read_text(encoding="utf-8", errors="ignore"),
                        encoding="utf-8",
                    )
        else:
            if original_path.is_absolute():
                try:
                    rel_path = original_path.relative_to(Path.cwd())
                except ValueError:
                    # For absolute paths outside cwd, create a reasonable relative path
                    # Keep the full path structure, just remove the root
                    rel_path = (
                        Path(*original_path.parts[1:])
                        if len(original_path.parts) > 1
                        else Path(original_path.name)
                    )
            else:
                rel_path = original_path

            # Create the destination path preserving directory structure
            if rel_path.parent != Path("."):
                dest = (
                    out_dir
                    / rel_path.parent
                    / f"{rel_path.stem}_debloated{rel_path.suffix}"
                )
                dest.parent.mkdir(parents=True, exist_ok=True)
            else:
                dest = out_dir / f"{rel_path.stem}_debloated{rel_path.suffix}"

            dest.write_text(content, encoding="utf-8")
            print(f"Created debloated version: {dest}")


# Create a default instance for backward compatibility
_default_remover = ConfigFileRemover()


def remove_unused_dependencies(
    cfg_files: List[str], unused_map: Dict[str, Set[str]], create_debloated: bool = False
) -> None:
    """Remove unused dependencies from config files.

    This is a convenience function that uses the default remover instance.
    """
    _default_remover.remove_unused_dependencies(cfg_files, unused_map, create_debloated)
