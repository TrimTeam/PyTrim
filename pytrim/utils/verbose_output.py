"""Enhanced verbose output utilities for PyTrim with improved formatting and colors."""

import colorama
from typing import List, Optional, Any


class VerboseFormatter:
    """Handles formatted verbose output with colors and sections."""

    def __init__(self):
        colorama.init(autoreset=True)
        self.indent_level = 0

    def section(self, title: str, color: str = colorama.Fore.CYAN) -> None:
        """Print a major section header."""
        separator = "=" * 60
        print(f"\n{color}{separator}")
        print(f"{title.center(60)}")
        print(f"{separator}{colorama.Style.RESET_ALL}")

    def subsection(self, title: str, color: str = colorama.Fore.YELLOW) -> None:
        """Print a subsection header."""
        print(f"\n{color}▶ {title}{colorama.Style.RESET_ALL}")
        print(f"{color}{'-' * (len(title) + 2)}{colorama.Style.RESET_ALL}")

    def info(self, message: str, indent: int = 0) -> None:
        """Print an info message with optional indentation."""
        spaces = "  " * indent
        print(f"{spaces}{message}")

    def success(self, message: str, indent: int = 0) -> None:
        """Print a success message."""
        spaces = "  " * indent
        print(f"{spaces}{colorama.Fore.GREEN}✓ {message}{colorama.Style.RESET_ALL}")


    def file_list(self, title: str, files: List[Any], base_path: Optional[Any] = None, max_items: int = 10) -> None:
        """Print a formatted list of files."""
        self.info(f"{title}: {len(files)} files")

        # Show first max_items files
        display_files = files[:max_items]
        for f in display_files:
            if base_path:
                try:
                    relative_path = f.relative_to(base_path)
                    self.info(f"   {relative_path}", indent=1)
                except (ValueError, AttributeError):
                    self.info(f"   {f}", indent=1)
            else:
                self.info(f"   {f}", indent=1)

        # Show count if there are more files
        if len(files) > max_items:
            remaining = len(files) - max_items
            self.info(f"  ... and {remaining} more files", indent=1)

    def package_list(self, title: str, packages: List[str], max_items: int = 15) -> None:
        """Print a formatted list of packages."""
        if not packages:
            self.info(f"{title}: None found")
            return

        self.info(f"{title}: {len(packages)} packages")

        # Show packages in a more compact format
        display_packages = sorted(packages)[:max_items]

        # Group packages for better readability
        for i in range(0, len(display_packages), 3):
            group = display_packages[i:i+3]
            package_line = " | ".join(f"{pkg}" for pkg in group)
            self.info(f"  {package_line}", indent=1)

        if len(packages) > max_items:
            remaining = len(packages) - max_items
            self.info(f"  ... and {remaining} more packages", indent=1)

    def processing_file(self, filepath: str, action: str = "Processing") -> None:
        """Print file processing status."""
        self.info(f"{action}: {colorama.Fore.BLUE}{filepath}{colorama.Style.RESET_ALL}")

    def skipping_file(self, filepath: str, reason: str) -> None:
        """Print file skipping status."""
        print(f"{colorama.Fore.YELLOW}⚠ Skipping {filepath}: {reason}{colorama.Style.RESET_ALL}")

    def found_unused(self, filepath: str, unused_items: List[str]) -> None:
        """Print unused imports found in a file."""
        if unused_items:
            self.info(f"Found unused imports in {colorama.Fore.MAGENTA}{filepath}{colorama.Style.RESET_ALL}:")
            for item in unused_items:
                self.info(f" {item}", indent=1)


# Global formatter instance
formatter = VerboseFormatter()


def verbose_info(message: str, verbose: bool, indent: int = 0) -> None:
    """Print info message only if verbose mode is enabled."""
    if verbose:
        formatter.info(message, indent)


def verbose_warning(message: str, verbose: bool, indent: int = 0) -> None:
    """Print warning message only if verbose mode is enabled."""
    if verbose:
        print(f"{'  ' * indent}{colorama.Fore.YELLOW}⚠ {message}{colorama.Style.RESET_ALL}")