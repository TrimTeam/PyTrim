import argparse
import json
import os
import subprocess as sp
import tempfile
from pathlib import Path

from pkginfo import BDist, SDist, Wheel

TMP_DIR = "/tmp"
TMP_REQUIREMENTS_TXT = "temp.txt"



def parse_file(path):
    w = None
    package = None
    version = None
    if path.endswith(".tar.gz"):
        w = SDist(path)
    if path.endswith(".egg"):
        w = BDist(path)
    if path.endswith(".whl"):
        w = Wheel(path)
    if w:
        package = w.name
        version = w.version

    return package, version


def run_pip_setup(setup_path):
    # Ensure the provided path is absolute
    setup_path = Path(setup_path).resolve(strict=True)
    current_dir = os.getcwd()
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = Path(tmp_dir) / "packages"
        pkg_dir.mkdir()

        # Change the current working directory
        os.chdir(setup_path)
        # Run pip install . in the virtual environment
        pip_options = [
            "pip3",
            "install",
            ".",
            "--ignore-installed",
            "--target",
            str(pkg_dir),
        ]

        cmd = sp.Popen(pip_options, stdout=sp.PIPE, stderr=sp.STDOUT)
        stdout, _ = cmd.communicate(None)
        stdout = stdout.decode("utf-8").splitlines()
        err = True
        package = None
        res = set()
        for line in stdout:
            # Parse lines that show a successful installation
            if "Successfully installed" in line:
                # Split the string into packages and versions
                packages = line.replace("Successfully installed ", "").split()
                for package in packages:
                    err = False
                    # Split the package string into name and version
                    name, version = package.rsplit("-", 1)  # get last "-" as separator
                    res.add((name, version))
        os.chdir(current_dir)
        if err:
            return False, err
        return True, res


def run_pip(input_string, is_local_resolution):
    res = set()
    if is_local_resolution:
        pip_options = ["pip3", "download", "-r", input_string, "-d", TMP_DIR]
    else:
        pip_options = [
            "pip3",
            "download",
            input_string.replace("=", "=="),
            "-d",
            TMP_DIR,
        ]

    cmd = sp.Popen(pip_options, stdout=sp.PIPE, stderr=sp.STDOUT)
    stdout, _ = cmd.communicate()

    stdout = stdout.decode("utf-8").splitlines()
    err = None
    package = None
    for line in stdout:
        if line.startswith("ERROR"):
            err = line
            break

        fname = None
        if "Downloading" in line:
            fname = os.path.join(TMP_DIR, os.path.basename(line.split()[1]))
        elif "File was already downloaded" in line:
            fname = line.split()[4]
        if fname:
            try:
                res.add(parse_file(fname))
            except Exception as e:
                err = str(e)
                break

    if err:
        return False, err

    return True, res