"""Package name utilities for dependency management."""
import re

def normalize(name: str) -> str:
    """Normalize package names to lowercase with hyphens."""
    return re.sub(r"[-_.]+", "-", name).lower()
