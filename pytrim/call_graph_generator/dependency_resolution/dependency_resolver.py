import argparse
import configparser
import csv
import json
import os
import re

import toml

from pypi_resolver import entrypoint


def parse_args():
    parser = argparse.ArgumentParser(description="Create dependencies json")
    parser.add_argument(
        "-d",
        "--directory",
        required=True,
        help="Directory of the application to process",
    )
    return parser.parse_args()


def get_package_name(app_path):
    setup_cfg_file = app_path + "/setup.cfg"
    setup_py_file = app_path + "/setup.py"
    pyproject_toml_file = app_path + "/pyproject.toml"
    # Check if setup.cfg file exists
    if os.path.exists(setup_cfg_file):
        config = configparser.ConfigParser()
        config.read(setup_cfg_file)
        if "metadata" in config.sections():
            if config["metadata"].get("name"):
                return config["metadata"].get("name")

    # Check if setup.py file exists
    if os.path.exists(setup_py_file):
        try:
            with open(setup_py_file) as file:
                setup_py_text = file.read()
                name_match = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", setup_py_text)
                name = name_match.group(1) if name_match else None
                if name:
                    return name
        except BaseException:
            return None

    # Check if pyproject.toml file exists
    if os.path.exists(pyproject_toml_file):
        try:
            config = toml.load(pyproject_toml_file)
            if "tool" in config and "poetry" in config["tool"]:
                return config["tool"]["poetry"].get("name")
        except BaseException:
            return None
    return None


def find_apps(coordinates):
    apps = list()
    for package in coordinates:
        if package["is_app"]:
            apps.append(package["product"] + ":" + package["version"])
    return apps


def load_csv(filename):
    package_names = []
    with open(filename) as file:
        csv_reader = csv.reader(file)
        package_names = [row[0] for row in csv_reader]
    return package_names


def process(app, app_path):
    resolved_deps_file = app_path + "/call_graph_data" + "/resolved_dependencies.json"
    os.makedirs(os.path.dirname(resolved_deps_file), exist_ok=True)
    if not os.path.exists(resolved_deps_file):
        appname = get_package_name(app_path)
        if not appname:
            appname = app
        status, res = entrypoint.run_pip(appname, False)
        response = entrypoint.get_response(app, status, res)
        if response["status"] and len(response["packages"]) > 0:
            app_name = app
            dependencies = [
                pkg["package"] + ":" + pkg["version"]
                for pkg in response["packages"].values()
                if pkg["package"] != appname
            ]
            save_output({app_name: dependencies}, resolved_deps_file)
            return
        status, res = entrypoint.run_pip_setup(app_path)
        response = entrypoint.get_response(appname, status, res)
        if response["status"] and len(response["packages"]) > 0:
            if len(response["packages"]) != 0:
                dependencies = [
                    pkg["package"] + ":" + pkg["version"]
                    for pkg in response["packages"].values()
                    if pkg["package"] != appname
                ]
                save_output({app: dependencies}, resolved_deps_file)
                return

        requirements_file = app_path + "/requirements.txt"
        if os.path.exists(requirements_file):
            status, res = entrypoint.run_pip(requirements_file, True)
            response = entrypoint.get_response(app, status, res)
            app_name = app
            if response["status"] and len(response["packages"]) > 0:
                dependencies = [
                    pkg["package"] + ":" + pkg["version"]
                    for pkg in response["packages"].values()
                    if pkg["package"] != appname
                ]
                save_output({app_name: dependencies}, resolved_deps_file)
                return

        requirements_file = app_path + "/requirements.txt"
        if os.path.exists(requirements_file):
            status, res = entrypoint.run_pip(requirements_file, True)
            response = entrypoint.get_response(app, status, res)
            if response["status"] and len(response["packages"]) > 0:
                app_name = app
                dependencies = [
                    pkg["package"] + ":" + pkg["version"]
                    for pkg in response["packages"].values()
                    if pkg["package"] != appname
                ]
                save_output({app_name: dependencies}, resolved_deps_file)
                return


def save_output(coord_list, resolved_deps_file):
    jsonString = json.dumps(coord_list, indent=2)
    jsonFile = open(resolved_deps_file, "w")
    jsonFile.write(jsonString)
    jsonFile.close()


def main():
    args = parse_args()
    app = os.path.basename(args.directory.strip("/"))
    process(app, args.directory)


if __name__ == "__main__":
    main()
