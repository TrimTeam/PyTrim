"""Core debloating functionality."""

from .file_remover import debloat_file
from .report_producer import create_dir_report, create_project_report

__all__ = [
    "debloat_file",
    "create_dir_report",
    "create_project_report",
]
