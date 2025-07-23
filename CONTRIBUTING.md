# Contributing to PyTrim
Thank you for your interest in contributing to PyTrim! This guide will help you get started with contributing to the project.

## Quick Start

1. **Fork and Clone**
   ```bash
   git clone https://github.com/TrimTeam/PyTrim.git
   cd pytrim
   ```

2. **Set Up Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   pre-commit install
   ```

3. **Run Tests**
   ```bash
   pytest
   ```

## Development Guidelines

### Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Run them manually:
```bash
black pytrim/ tests/
isort pytrim/ tests/
flake8 pytrim/ tests/
mypy pytrim/
```

### Testing

Write tests for all new features and bug fixes:

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
- Update documentation in `docs/` for new features
- Include examples in docstrings where helpful

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation

3. **Commit your changes**
   ```bash
   git commit -m "Add feature: clear description of changes"
   ```

4. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## Types of Contributions

- **Bug Reports**: Use GitHub issues with reproduction steps
- **Feature Requests**: Describe use cases and proposed implementation
- **Code Contributions**: Bug fixes, new features, performance improvements
- **Documentation**: Fix typos, add examples, improve clarity

## Adding New File Type Support

To add support for a new file type:

1. **Create an Extractor**
   ```python
   class NewFileExtractor(BaseExtractor):
       def can_handle(self, file_path: Path) -> bool:
           return file_path.suffix == '.newtype'

       def extract_dependencies(self, file_path: Path) -> Set[str]:
           # Implementation here
           pass
   ```

2. **Create a Remover**
   ```python
   class NewFileRemover(BaseRemover):
       def can_handle(self, file_path: Path) -> bool:
           return file_path.suffix == '.newtype'

       def remove_dependencies(self, file_path: Path, unused_deps: List[str]) -> bool:
           # Implementation here
           pass
   ```

3. **Add comprehensive tests**
4. **Update documentation**

## Code Review

All submissions go through code review:

- Automated checks must pass (tests, style, coverage)
- Manual review for code quality and architecture
- Address reviewer feedback promptly

## Getting Help

- Check existing documentation and examples
- Search GitHub issues for similar problems
- Open a new issue with detailed information
- Join GitHub Discussions for general questions

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
