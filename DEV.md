# Development Guide

## Setting up Development Environment
```bash
git clone https://github.com/karyotakisg/PyTrim.git
cd PyTrim
pip install -e ".[dev]"
pre-commit install
```

**Important**: This project uses pre-commit hooks for code quality. You must install pre-commit hooks before making commits.

## Development Installation
```bash
git clone https://github.com/karyotakisg/PyTrim.git
cd PyTrim
pip install -e ".[dev]"
```

## Running Tests
```bash
pytest
```

## Code Formatting
```bash
black pytrim/
isort pytrim/
```

## Type Checking
```bash
mypy pytrim/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

**Before contributing:**
1. Install development dependencies: `pip install -e ".[dev]"`
2. Install pre-commit hooks: `pre-commit install`
3. Make sure all pre-commit checks pass before committing

## Architecture

The package is organized into several specialized modules:

### Core Modules
- **`extractors/`**: File type-specific dependency extractors
  - `python_files.py`: Handles setup.py files
  - `requirements_files.py`: Processes requirements.txt and .in files
  - `toml_files.py`: Manages pyproject.toml, poetry.lock, Pipfile
  - `yaml_files.py`: Processes YAML configuration files
  - `shell_files.py`: Handles shell scripts
  - `docker_files.py`: Processes Dockerfiles
  - `ini_files.py`: Manages setup.cfg and tox.ini
  - `documentation_files.py`: Processes .md and .rst files

- **`removers/`**: File type-specific dependency removers
  - `handlers/`: Specialized removal logic for each file type
  - `line_utils.py`: Utility functions for line-by-line processing

- **`analyzers/`**: Dependency analysis logic
  - `module_analyzer.py`: Finds used modules in Python code
  - `dependency_analyzer.py`: Identifies unused dependencies

- **`utils/`**: Common utilities
  - `package_utils.py`: Package name normalization

- **`core/`**: Core functionality
  - `file_remover.py`: Python file trimming
  - `report_producer.py`: Report generation

- **`cli/`**: Command line interface
