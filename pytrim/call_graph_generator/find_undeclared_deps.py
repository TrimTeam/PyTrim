import os
import json
from ..extractors.dependency_extractor import extract_deps
import sys
import importlib
import sysconfig

BUILD_PACKAGES = [
   "setuptools",
   "wheel", 
   "pip",
   "build",
   "installer",
   "pep517",
   "pyproject-hooks",
   "setuptools-scm",
   "twine"
]

def is_stdlib_module(module_name):
    """
    Check if a module is part of the Python standard library.
    """
    # 1) Python 3.10+: full stdlib list
    if hasattr(sys, "stdlib_module_names"):
        return module_name in sys.stdlib_module_names

    # 2) "Built-in" compiled modules (these come with Python too)
    if module_name in sys.builtin_module_names:
        return True

    # 3) Pure-Python stdlib: find its file and see if it lives under the stdlib dir
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None or not spec.origin:
            return False
        stdlib_dir = sysconfig.get_paths()["stdlib"]
        try:
            return os.path.commonpath([spec.origin, stdlib_dir]) == stdlib_dir
        except ValueError:
            return False
    except (ImportError, AttributeError, ValueError):
        return False

def find_direct_deps_from_config(cfg_files):
    direct_deps = []
    for cfg in cfg_files:
        direct_deps.extend(extract_deps(cfg))
    return direct_deps

def find_key_of_value(d, value):
    """
    Find the key in a dictionary that corresponds to a given value.
    """
    for k, values in d.items():
        for v in values:
            if v.strip() == value:
                return k
    return None

def find_undeclared_deps(call_graph, direct_deps):
    mappings = get_all_mappings()
    undeclared_deps = []
    with open(call_graph, 'r') as f:
        call_graph = json.load(f)
    modules_import_names = call_graph['modules']['external'].keys()
    for module in modules_import_names:
        # TODO: if package_name is None, we should try to find it
        package_name = find_key_of_value(mappings, module.strip())
        if package_name not in direct_deps and package_name \
            is not None and not is_stdlib_module(package_name)\
            and package_name not in BUILD_PACKAGES:
            undeclared_deps.append(package_name)
    return undeclared_deps

def get_all_mappings():
    path = os.path.join("pytrim", 'import_mappings.json')
    with open(path, 'r') as f:
        mappings = json.load(f)
    return mappings

def get_undeclared_deps(cg_path, cfg_files):
    if not os.path.exists(cg_path):
        print(f"\n Call graph file {cg_path} does not exist.")
        return
    direct_deps = find_direct_deps_from_config(cfg_files)
    unused_deps = find_undeclared_deps(cg_path, direct_deps)
    return unused_deps

def find_package_name_of_cg_module(module):
    #TODO
    print("test")