import os
import json
from ..utils.package_utils import normalize
from pytrim.dynamic_dependency_resolution import DynamicDependenciesResolver
from ..analyzers.module_analyzer import ensure_mappings

PYTRIM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_deps_used_in_cg(call_graph, source_dir):
    direct_deps = set()
    for dep in call_graph['depset']:
        direct_deps.add(normalize(dep['product']))
    dynamic_deps = DynamicDependenciesResolver.process_project(source_dir)
    all_direct_deps = set(direct_deps) | set(dynamic_deps)
    return all_direct_deps

def find_unused_deps(call_graph, direct_deps, mappings):
    unused_deps = []
    external_modules = call_graph['modules']['external'].keys()
    for dep in direct_deps:
        import_names = mappings[dep.lower()]
        if all(import_name not in external_modules for import_name in import_names):
            unused_deps.append(dep)
    return unused_deps

def get_unused_deps(cg_path, source_dir):
    if not os.path.exists(cg_path):
        print(f"\n Call graph file {cg_path} does not exist.")
        return
    with open(cg_path, 'r') as f:
        call_graph = json.load(f)
    direct_deps = find_deps_used_in_cg(call_graph, source_dir)
    mappings = get_mappings(direct_deps)
    unused_deps = find_unused_deps(call_graph, direct_deps, mappings)
    return unused_deps

def get_mappings(direct_deps):
    mappings_file = os.path.join(PYTRIM_ROOT, "utils", "import_mappings.json")
    mappings = ensure_mappings(direct_deps, mappings_file)
    return mappings