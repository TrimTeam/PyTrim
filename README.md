# PyTrim

A Python tool for trimming of unused imports and dependencies from Python projects.
PyTrim helps keep your codebase clean by automatically removing unused dependencies from both source code and configuration files.

## Features

- **Auto-Detection**: Automatically finds unused dependencies without manual specification
- **Multi-format Support**: Handles Python files, requirements.txt, pyproject.toml, setup.py, poetry.lock, Pipfile, YAML files, Docker files, and more
- **Intelligent Analysis**: Uses AST parsing to accurately identify unused imports and dependencies
- **Modular Architecture**: Clean, extensible design with separate extractors and removers for different file types
- **CLI Interface**: Easy-to-use command line interface with smart defaults
- **Report Generation**: Creates detailed Markdown reports of changes
- **Git Integration**: Automatic branch creation and PR generation
- **Professional Package**: Ready for PyPI distribution with proper setup and documentation

## Installation

### PyPI Installation
```bash
pip install pytrim
```

### Source Installation
```bash
git clone https://github.com/karyotakisg/PyTrim.git
cd PyTrim
pip install .
```

### Install PyCG (optional)
When pytrim is installed from Pypi or source code, to run unused packages detection with call graph you need to install pycg.

1. Install PyCG from source:
    ```bash
    git clone https://github.com/gdrosos/PyCG.git && \
    cd PyCG && \
    pip3 install .
    ```
2. Ensure the PyCG entrypoint is in PATH:
   ```bash
    PATH="$HOME/.local/bin:$PATH"
   ```

## Use PyTrim inside a Docker container

1. Install `docker` (https://docs.docker.com/engine/install/)

2. Clone this repository:
      ```bash
      git clone https://github.com/TrimTeam/PyTrim.git
      ```

3. Enter the source code directory:

      ```bash
      cd PyTrim
      ```

4.  Build docker image:
    ```bash
    docker build -t pytrim .
    ```

5. Run docker container:
    ```bash
    docker run --rm -it -v /path/to/project:/project pytrim
    ```

    The Dockerfile is configured to:
    - Set working directory to `/project`
    - Mount your project at `/project`
    - Open bash terminal by default (`CMD ["/bin/bash"]`)

6. Then, you are ready to run pytrim:
    ```bash
    pytrim .
    ```


## Usage

After installation, use the `pytrim` command:

```bash
pytrim [-h] [-f FILE | -d DIRECTORY] [-u UNUSED_IMPORTS [UNUSED_IMPORTS ...]] [-r] [-o] [-pr] [-dp | -fd | -cg] [-v] [-V]
              [--generate-mappings [GENERATE_MAPPINGS ...]] [--mappings-file MAPPINGS_FILE] [-e EXCLUDE [EXCLUDE ...]]
              [project]
```

### Options
- `-f FILE, --file FILE`: Process a single Python file
- `-d DIRECTORY, --directory DIRECTORY`: Process all `.py` files in a directory
- `-u UNUSED_IMPORTS [...], --unused-imports UNUSED_IMPORTS [...]`: List of unused imports/dependencies to remove (optional - will auto-detect if not specified)
- `-r, --report`: Generate reports about trimmed packages in the `reports` folder
- `-o, --output`: Create new debloated files in folder `output` instead of overwriting originals
- `-pr, --pull-request`: Create a Git branch and GitHub Pull Request with changes
- `-V, --version`: Show version information
- `-v, --verbose`: Show detailed information about the trimming process.
- `-dp, --deptry`: Use deptry to find unused imports (requires deptry installed).
- `-fd, --fawltydeps`: Use fawltydeps to find unused dependencies (requires fawltydeps installed).
- `-cg, --call-graph`: Use call graph analysis to find unused imports (requires PyCG installed).
- `--generate-mappings`: Generate import mappings JSON file for specified packages (or use discovered packages if none specified).
- `--mappings-file`: Use custom import mappings JSON file instead of built-in mappings.
- `-e, --exclude`: Exclude specific dependencies from the removal process.E.g. a transitive dependency that needs its version pinned.
- `PROJECT`: Project root directory (default: current directory)

### Examples

**Trim current project:**
```bash
pytrim
```

**Auto-detect unused dependencies and remove them from a project:**
```bash
pytrim path/to/project/
```

**Remove unused imports from a single file:**
```bash
pytrim -f src/main.py -u os sys pandas
```

**Process all Python files in a directory:**
```bash
pytrim -d src/ -u requests json numpy
```

**Trim current project with reporting:**
```bash
pytrim -r
```

**Auto-detect specific project with reporting:**
```bash
pytrim project/ -r
```

**Clean an entire project with specific packages:**
```bash
pytrim project/ -u pandas matplotlib seaborn -r
```

**Create a Pull Request for current project:**
```bash
pytrim -pr
```

## Output Modes

### Default Mode
Files are modified in place. Only files that need changes are updated.

### Report Mode (`-r`)
- **Trimmed files**: Saved to `output/` directory with `_trimmed` suffix
- **Reports**: Generated in `reports/` directory with detailed analysis

### Pull Request Mode (`-pr`)
- Files modified in place
- Creates Git branch with timestamp
- Generates `project_report.md` in project root
- Automatically creates GitHub Pull Request

## Development

For development setup, contributing guidelines, and architecture details, see [DEV.md](DEV.md).

## Requirements

- Python 3.10+
- `tomli` (for Python < 3.11, automatically installed)
- `tqdm`
- `fawltydeps`
- `pkginfo`
- `flask`
- `toml`
- `colorama`

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please see [DEV.md](DEV.md) for detailed development setup and contribution guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/pytrim/pytrim/issues)
- **Documentation**:
- **Source Code**: [GitHub](https://github.com/pytrim/pytrim)
