# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.2.0] - 2025-10-05

### Added

- **Dynamic Dependency Resolution:** A new feature to generate a list of dependencies based on install-time information (improves detection of unused dependencies).
- **Imports Auto-Detection:** Automatically detect unused dependencies in Python files without needing manual specification.
- Add a 10-minute timeout for each detection engine to prevent hangs.
- Add detailed "Commit Message Guidelines" and project architecture information to the `CONTRIBUTING.md` file.
- Add a comprehensive `.gitignore` file to the repository.

### Changed

- **CLI Behavior:** The `-cg` flag has been removed (it is the default detection method).
- **CLI Behavior:** The `-r` (report) and `-o` (output) flags are now separate options for more flexible control over output.
- **CLI Output:** Improved logging and command-line output for better usability.
- Improve dependency detection logic for `setup.py` and `*.in` files.
- Overhaul and consolidate all developer documentation into a single, professional `CONTRIBUTING.md` file.

---

## [0.1.2] - 2025-07-24

### Added

- Initial public release of the `pytrim` package.
- Core functionality for detecting unused project dependencies.
- Command-line interface (`pytrim`) for running analysis.
- This `CHANGELOG.md` file to track project history.

### Changed

- Corrected the `LICENSE` file to properly list copyright holders. The project remains under the MIT License.
