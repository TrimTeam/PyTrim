import os
import json
from tempfile import TemporaryDirectory
from . import utils
import difflib
from ..utils.package_utils import normalize
import colorama

class DependencyResolverPytrim:
    def __init__(self, path:str,tmp_install_dir):
        self.source_dir = path
        self.project = os.path.basename(os.path.abspath(path))
        self.tmp_install_dir = tmp_install_dir
        self.package = None
        self.direct_deps = None

    
    def _install_package(self):  
        cmd = [
            'pip3',
            'install',
            '-t', self.tmp_install_dir,
            '--ignore-installed',
            '--upgrade',
            '--force-reinstall',
            self.source_dir
        ]
        try:
            ret, out, err = utils.run_cmd(cmd)
        except Exception as e:
            print(colorama.Fore.RED + f"Error: {e}, while installing {self.project} in {self.tmp_install_dir}" + colorama.Style.RESET_ALL)
            print(colorama.Fore.RED + "Make sure that you have setup.py or pyproject.toml in the project"+ colorama.Style.RESET_ALL)

    def _resolve_deps(self):
        cmd = [
            'pipdeptree',
            '--path', self.tmp_install_dir,
            '--json'
        ]
        try:
                ret, out, err = utils.run_cmd(cmd, cwd=self.tmp_install_dir)
                deps_raw = json.loads(out)
                self.package_name = self._get_package_name(deps_raw)
                self.direct_deps = self._get_direct_deps(deps_raw)
        except Exception as e:
            print(f"Error: {e}, while resolving dependencies for {self.project}")

    def _get_package_name(self, deps_all):
        # Get the package that is dependency of none
        # If multiple, get the most similar to project name
        # TODO: Handle case where package name is totally different than project name
        packages = [package['package']['package_name'] for package in deps_all]
        for package in deps_all:
            dependencies = package['dependencies']
            for dep in dependencies:
                if dep['package_name'] in packages:
                    packages.remove(dep['package_name'])
        if len(packages) > 1:
            return self._get_the_most_similar_package(packages)
        elif len(packages) == 1:
            return packages[0]

    def _get_the_most_similar_package(self, packages):
        most_similar = difflib.get_close_matches(self.project.split("/")[-1], packages, n=1, cutoff=0.0000001)
        return most_similar[0]

    def _get_direct_deps(self, deps_all):
        direct_deps = set()
        for dep in deps_all:
            if dep['package']['package_name'] == self.package_name:
                for dependency in dep['dependencies']:
                    dep_name = dependency['package_name']
                    #dep_version = dependency['installed_version']
                    direct_deps.add(normalize(dep_name))
        return direct_deps
                    
    def run(self):
        self._install_package()
        self._resolve_deps()

def process_project(path):
    with TemporaryDirectory() as tmp_install_dir:
        resolver = DependencyResolverPytrim(path, tmp_install_dir)
        resolver.run()
        return resolver.direct_deps