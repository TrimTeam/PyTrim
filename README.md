# PyTrim

[![Latest Release](https://img.shields.io/pypi/v/pytrim.svg)](https://pypi.org/project/pytrim/)
[![Python Version](https://img.shields.io/pypi/pyversions/pytrim)](https://pypi.python.org/pypi/pytrim/)
[![PyPI Statistics](https://img.shields.io/pypi/dm/pytrim.svg)](https://pypistats.org/packages/pytrim)
[![Docker Pulls](https://img.shields.io/docker/pulls/karakatsanis/pytrim.svg)](https://hub.docker.com/r/karakatsanis/pytrim)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/TrimTeam/PyTrim/blob/main/LICENSE)

A Python tool for trimming of unused imports and dependencies from Python projects.
PyTrim helps keep your codebase clean by automatically removing unused dependencies from both source code and configuration files.

## Features

- **Auto-Detection**: Automatically finds unused dependencies without manual specification
- **Multi-format Support**: Handles Python files, requirements.txt, pyproject.toml, setup.py, poetry.lock, Pipfile, YAML files, Dockerfiles, and more
- **Modular Architecture**: Extensible design with separate extractors and removers for different file types
- **CLI Interface**: Easy-to-use command line interface with smart defaults
- **Report Generation**: Creates detailed Markdown reports of changes
- **Git Integration**: Automatic branch creation and PR generation

## Installation

### Docker (Recommended)

1.  **Install Docker**  
    Follow the official instructions: https://docs.docker.com/engine/install/

2.  **Navigate to Your Project's Source Code Directory**  
    In your terminal, change to the root directory of the source code you want to analyze.
    ```bash
    cd /path/to/your/source
    ```

3.  **Run the PyTrim Container**  

       **For Linux/macOS:**
       ```bash
       docker run --rm -it -v "$(pwd):/project" karakatsanis/pytrim
       ```
    
       **For Windows (PowerShell):**
       ```bash
       docker run --rm -it -v "${PWD}:/project" karakatsanis/pytrim
       ```
    
    This command:
    - Downloads the PyTrim image from Docker Hub (first time only)
    - Mounts your current directory into the container at `/project`
    - Drops you into a shell inside the container

4. **Run PyTrim inside the container**
   ```bash
   pytrim
   ```

   You can use any PyTrim commands and options. For example:
   ```bash
   pytrim --help
   pytrim -r
   pytrim -d src/
   ```

5. **Exit the container**
   ```bash
   exit
   ```

### PyPI
```bash
pip install pytrim
```

**Note**: Call graph analysis (the default detection method) requires the external tool PyCG. For the simplest experience with all features enabled, we recommend using the Docker image.

#### Install PyCG (optional)
Call graph analysis is the default detection method, but it requires the external tool `PyCG`. 
If you install `PyTrim` via PyPI, you must install `PyCG` manually for this feature to work. 

1. Install PyCG from source: 
    ```bash
    git clone https://github.com/gdrosos/PyCG.git
    cd PyCG
    pip install .
    ```
2. Ensure the PyCG entrypoint is in PATH:
    For the change to be permanent, add the following line to your shell's configuration file (e.g., `~/.bashrc`, `~/.zshrc`):
    ```bash
    export PATH="$HOME/.local/bin:$PATH"
    ```
    After saving the file, restart your terminal or run `source ~/.bashrc` (or your respective config file) to apply the changes.

## Usage

After installation, use the `pytrim` command:

```bash
pytrim [-h] [-f FILE] [-d DIRECTORY] [-u UNUSED_IMPORTS [UNUSED_IMPORTS ...]] [-r] [-o] [-pr] [-dp | -fd] [-v] [-V] 
              [-gm [GENERATE_MAPPINGS ...]] [-mf MAPPINGS_FILE] [-e EXCLUDE [EXCLUDE ...]] 
              [project]
```

### Options
- `-h, --help`: Show help message and exit
- `-f FILE, --file FILE`: Process a single Python file
- `-d DIRECTORY, --directory DIRECTORY`: Process all `.py` files in a directory
- `-u UNUSED_IMPORTS [...], --unused-imports UNUSED_IMPORTS [...]`: List of unused imports/dependencies to remove (optional - will auto-detect if not specified)
- `-r, --report`: Generate reports about trimmed packages in the `pytrim_reports` folder
- `-o, --output`: Create new debloated files in folder `pytrim_output` instead of overwriting originals
- `-pr, --pull-request`: Create a Git branch and GitHub Pull Request with changes
- `-v, --verbose`: Show detailed information about the trimming process.
- `-V, --version`: Show version information
- `-dp, --deptry`: Use deptry to find unused imports (requires deptry installed).
- `-fd, --fawltydeps`: Use fawltydeps to find unused dependencies (requires fawltydeps installed).
- `-gm, --generate-mappings`: Generate import mappings JSON file for specified packages (or use discovered packages if none specified), then run the full PyTrim analysis using the generated mappings.
- `-mf, --mappings-file MAPPINGS_FILE`: Use custom import mappings JSON file instead of built-in mappings.
- `-e, --exclude`: Exclude specific dependencies from the removal process. E.g., a transitive dependency that needs its version pinned.
- `PROJECT`: Project root directory (default: current directory)

### Examples

**Show help and all available options:**
```bash
pytrim --help
```

**Trim current project:**
```bash
pytrim
```

**Auto-detect and remove unused dependencies from a project:**
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

### Output Mode (`-o, --output`)
Creates new debloated files in the `pytrim_output/` directory instead of overwriting the original files.

### Report Mode (`-r, --report`)
Generates detailed Markdown reports in the `pytrim_reports/` directory with analysis of trimmed packages and dependencies.

### Pull Request Mode (`-pr, --pull-request`)
- Files modified in place
- Creates Git branch with timestamp (format: `debloat/YYYYMMDDHHMMSS`)
- Generates `project_report.md` in project root
- Automatically creates a GitHub Pull Request with the changes (requires `gh` CLI)
- **Requirements**: Git repository, `git` and `gh` CLI tools installed

### Combined Modes
You can combine output modes:
- `-r -o`: Generate reports AND save debloated files to `pytrim_output/`
- `-r -pr`: Generate reports AND create pull request
- All modes can be combined as needed

## Requirements

- Python 3.10+
- `git` - Required for version control operations
- `gh` CLI - Required for pull request creation (`-pr` flag)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, contribution guidelines, and project architecture details.

## Support

- **Issues**: [GitHub Issues](https://github.com/TrimTeam/PyTrim/issues)
- **Source Code**: [GitHub](https://github.com/TrimTeam/PyTrim)

## License

MIT License - see [LICENSE](LICENSE) file for details.
