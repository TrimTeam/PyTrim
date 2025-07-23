import os
import json

def find_deps_used_in_cg(call_graph):
    direct_deps = set()
    for dep in call_graph['depset']:
        direct_deps.add(dep['product'])
    return direct_deps

def find_unused_deps(call_graph, direct_deps, mappings):
    unused_deps = []
    external_modules = call_graph['modules']['external'].keys()
    for dep in direct_deps:
        import_names = mappings[dep.lower()]
        if all(import_name not in external_modules for import_name in import_names):
            unused_deps.append(dep)
    return unused_deps

def get_unused_deps(cg_path, mappings):
    if not os.path.exists(cg_path):
        print(f"\n Call graph file {cg_path} does not exist.")
        return
    with open(cg_path, 'r') as f:
        call_graph = json.load(f)
    direct_deps = find_deps_used_in_cg(call_graph)
    unused_deps = find_unused_deps(call_graph, direct_deps, mappings)
    return unused_deps