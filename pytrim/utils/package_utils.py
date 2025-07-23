"""Package name utilities for dependency management."""


def normalize(name: str) -> str:
    """Normalize package names to lowercase with hyphens."""
    return name.lower().strip().replace("_", "-")
