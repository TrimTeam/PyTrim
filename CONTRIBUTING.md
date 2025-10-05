# Contributing to PyTrim

Thank you for your interest in contributing to PyTrim! This guide will help you get started with contributing to the project.

## Quick Start

### 1. Fork and Clone

```bash
git clone https://github.com/TrimTeam/PyTrim.git
cd PyTrim
```

### 2. Set Up Development Environment

**Option A: Local Virtual Environment (venv)**

```bash
python -m venv venv

# On Linux/macOS
source venv/bin/activate
# On Windows (PowerShell)
.\venv\Scripts\activate

pip install -e ".[dev]"
pre-commit install
```

**Important**: This project uses pre-commit hooks for code quality. You must install pre-commit hooks before making commits.

**Option B: Docker Environment**

This workflow enables "live-reloading," so your code changes appear instantly inside the container without needing to rebuild.

1. **Build the development Docker image:**
   ```bash
   docker build --build-arg BUILD=dev -t pytrim:dev .
   ```

2. **Run the development container:**

   This command starts the container and mounts your local `PyTrim` source code into the `/app` directory.

   **For Linux and macOS:**
   ```bash
   docker run --rm -it -v "$(pwd):/app" pytrim:dev
   ```

   **For Windows (PowerShell):**
   ```bash
   docker run --rm -it -v "${PWD}:/app" pytrim:dev
   ```

3. **(Optional) Testing on an External Project**

   To test your live `PyTrim` code on another project, use a second `-v` flag to mount that project into the `/project` directory.

   ```bash
   docker run --rm -it -v "$(pwd):/app" -v "/path/to/your/source:/project" pytrim:dev
   ```

### 3. Run Tests

```bash
pytest
```

## Project Architecture

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

## Development Guidelines

### Code Quality Tools

The following tools are run automatically on each commit due to the `pre-commit` hooks:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

You can also run them manually:

```bash
black pytrim/ tests/
isort pytrim/ tests/
flake8 pytrim/ tests/
mypy pytrim/
```

### Testing

Please write tests for all new features and bug fixes.

```bash
# Run all tests
pytest

# Run specific test
pytest tests/unit/test_extractors.py

# Run with coverage
pytest --cov=pytrim --cov-report=html
```

### Documentation

- Use Google-style docstrings
- Update documentation in `docs/` for any new or changed features
- Include examples in docstrings where helpful

## Pull Request Process

1. **Create a feature branch** from the main branch.
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** ensuring to:
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation

3. **Commit your changes** with a clear and descriptive commit message.
   ```bash
   git commit -m "feat: Add support for a new file type"
   ```

4. **Push your branch and create a Pull Request** against the main branch.
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Guidelines

This project follows the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification. This leads to a more readable and structured commit history.

Each commit message consists of a **header**, a **body**, and a **footer**. The header has a special format that includes a **type**, a **scope** (optional), and a **subject**:

```
<type>(optional scope): <subject>
<BLANK LINE>
[optional body]
<BLANK LINE>
[optional footer]
```

Please use the following types when creating your commit messages:

- **build**: Changes that affect the build system or external dependencies
- **chore**: Routine maintenance, dependency updates, general tasks
- **ci**: Changes to CI configuration files and scripts
- **docs**: Documentation-only changes
- **feat**: A new feature
- **fix**: A bug fix
- **perf**: A code change that improves performance
- **refactor**: Code restructuring without changing external behavior
- **revert**: A commit that reverts a previous commit
- **style**: Code style, formatting (no code logic change)
- **test**: Adding missing tests or correcting existing tests

**Example:**
```
fix(parser): correctly handle multiline dependency strings

Previously, the parser would fail on dependencies in pyproject.toml
that spanned multiple lines. This change updates the regex to
correctly capture these cases.
```

## Types of Contributions

We welcome many types of contributions, including:

- **Bug Reports**: Use GitHub issues with clear reproduction steps
- **Feature Requests**: Describe your use case and proposed implementation
- **Code Contributions**: Bug fixes, new features, and performance improvements
- **Documentation**: Fix typos, add examples, and improve clarity

## Adding New File Type Support

To add support for a new file type:

1. **Create a new Extractor class** in the `extractors/` directory
   ```python
   class NewFileExtractor(BaseExtractor):
       def can_handle(self, file_path: Path) -> bool:
           return file_path.suffix == '.newtype'

       def extract_dependencies(self, file_path: Path) -> Set[str]:
           # Implementation here
           pass
   ```

2. **Create a new Remover class** in the `removers/` directory
   ```python
   class NewFileRemover(BaseRemover):
       def can_handle(self, file_path: Path) -> bool:
           return file_path.suffix == '.newtype'

       def remove_dependencies(self, file_path: Path, unused_deps: List[str]) -> bool:
           # Implementation here
           pass
   ```

3. **Write comprehensive tests** for both the extractor and remover

4. **Update documentation** to reflect the new file type support

## Code Review

All submissions go through code review:

- Automated checks must pass (tests, style, coverage)
- Manual review for code quality and architecture
- Address reviewer feedback promptly

## Getting Help

- Check existing documentation and examples
- Search existing GitHub issues for similar problems
- Open a new issue with detailed information

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
