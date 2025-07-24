"""Setup script for PyTrim."""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read version from the package
version_file = this_directory / "pytrim" / "__init__.py"
version = {}
with open(version_file) as f:
    for line in f:
        if line.startswith("__version__"):
            exec(line, version)
            break

setup(
    name="pytrim",
    version=version.get("__version__", "0.1.2"),
    description="Auto-detect and trim unused dependencies from Python projects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TrimTeam/PyTrim",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: System :: Archiving :: Packaging",
    ],
    python_requires=">=3.10",
    install_requires=[
        "tomli>=1.2.0;python_version<'3.11'",  # For TOML parsing in older Python versions
        "tqdm>=4.64.0",
        "fawltydeps",
        "pkginfo",
        "flask",
        "toml",
        "colorama",  # For colored output in CLI
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
        ],
        "docs": [],
    },
    entry_points={
        "console_scripts": [
            "trim=pytrim.cli.cli:main",
            "pytrim=pytrim.cli.cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/pytrim/pytrim/issues",
        "Source": "https://github.com/pytrim/pytrim",
        "Documentation": "https://pytrim.readthedocs.io/",
    },
    keywords="dependencies, imports, cleanup, trim, python, optimization, auto-detection, unused",
    include_package_data=True,
    zip_safe=False,
)
