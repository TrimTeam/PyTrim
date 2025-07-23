import argparse
import json
import os
import subprocess as sp
import tempfile
from pathlib import Path

import flask
from flask import jsonify, make_response, request
from pkginfo import BDist, SDist, Wheel

TMP_DIR = "/tmp"
TMP_REQUIREMENTS_TXT = "temp.txt"


##### RESOLVER ######


def create_requirements_file(requirements):
    with open(TMP_REQUIREMENTS_TXT, "w") as f:
        for item in requirements:
            f.write("%s\n" % item)


def delete_requirements_file():
    if os.path.exists(TMP_REQUIREMENTS_TXT):
        os.remove(TMP_REQUIREMENTS_TXT)


def get_response(input_string, resolution_status, resolution_result):
    res = {"input": input_string, "status": resolution_status}
    if resolution_status:
        res["packages"] = {}
        for package, version in resolution_result:
            if package:
                res["packages"][package] = {"package": package, "version": version}
    else:
        res["error"] = resolution_result
    return res


def get_response_for_api(resolution_status, resolution_result):
    res = {}
    if resolution_status:
        list1 = []
        for package, version in resolution_result:
            if package:
                list1.append({"product": package, "version": version})
        res = list1
    else:
        res["error"] = resolution_result
    return res


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


###### FLASK API ######
app = flask.Flask("api")
app.config["DEBUG"] = True


@app.route("/", methods=["GET"])
def home():
    return """<h1>PyPI Resolver</h1>
    <p>An API for resolving PyPI dependencies.</p>
    <p>API Endpoint for PyPI Packages: /dependencies/{packageName}/{version}<p>
    <p><b>Note</b>: The {version} path parameter is optional <p>
    <p>API Endpoint for Local Projects: /resolve_dependencies<p>
    <p><b>Note</b>: Should recieve through a POST Request a list of multiple dependencies as defined on the requirements.txt file, separated by commas <p>
    """


@app.errorhandler(404)
def page_not_found(e):
    return (
        """<h1>404</h1><p>The resource could not be found.</p>
    <p>API Endpoint: /dependencies/{packageName}/{version}<p>""",
        404,
    )


@app.route("/dependencies/<packageName>", methods=["GET"])
def resolver_api_without_version(packageName):
    if not packageName:
        return make_response(
            jsonify({"Error": "You should provide a mandatory {packageName}"}), 400
        )

    status, res = run_pip(packageName, False)

    return jsonify(get_response_for_api(status, res))


@app.route("/dependencies/<packageName>/<version>", methods=["GET"])
def resolver_api_with_version(packageName, version):
    if not packageName:
        return make_response(
            jsonify({"error": "You should provide `input` query parameters"}), 400
        )

    status, res = run_pip(packageName + "=" + version, False)

    return jsonify(get_response_for_api(status, res))


@app.route("/resolve_dependencies", methods=["POST"])
def multiple_dependencies_resolver_api():
    try:
        request_data = (
            str(request.data.decode("utf-8")).replace("[", "").replace("]", "")
        )
        requirements = request_data.split(",")
        create_requirements_file(requirements)

    except Exception as e:
        delete_requirements_file()
        return str(e)
    status, res = run_pip(TMP_REQUIREMENTS_TXT, True)

    delete_requirements_file()

    return jsonify(get_response_for_api(status, res))


def deploy(host="0.0.0.0", port=5000):
    app.run(threaded=True, host=host, port=port)


###### CLI ######


def get_parser():
    parser = argparse.ArgumentParser("Resolve dependencies of PyPI packages")
    parser.add_argument(
        "-i",
        "--input-package",
        type=str,
        help=(
            "Input package should be a string of a package name or the names of "
            "multiple packages separated by spaces. Examples: "
            "'django' or 'django=3.1.3' or 'django wagtail'"
        ),
    )
    parser.add_argument(
        "-r",
        "--requirements-file",
        type=str,
        help=(
            "The path of the requirements.txt file. "
            "When specified, the dependencies of a local project are resolved"
        ),
    )
    parser.add_argument("-o", "--output-file", type=str, help="File to save the output")
    parser.add_argument("-f", "--flask", action="store_true", help="Deploy flask api")
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    input_string = args.input_package
    output_file = args.output_file
    cli_args = (input_string, output_file)
    flask = args.flask
    requirements_path = args.requirements_file

    # Handle options
    if flask and any(x for x in cli_args):
        message = "You cannot use any other argument with --flask option."
        raise parser.error(message)
    if input_string and requirements_path:
        message = "You should always use only one of  --input-package or --local-project when you want to run the cli."
        raise parser.error(message)
    if not flask and not input_string and not requirements_path:
        message = "You should always use --input or --local-project option when you want to run the cli."
        raise parser.error(message)

    if flask:
        deploy()
        return

    if input_string:
        status, res = run_pip(input_string, False)
    else:
        if not os.path.isfile(requirements_path):
            message = (
                "Could not find the requirements file specified on: "
                + requirements_path
            )
            raise parser.error(message)
        status, res = run_pip(requirements_path, True)
        input_string = requirements_path

    if output_file:
        with open(output_file, "w") as outfile:
            json.dump(get_response(input_string, status, res), outfile, indent=4)
    else:
        print(json.dumps(get_response(input_string, status, res), indent=4))


if __name__ == "__main__":
    main()
