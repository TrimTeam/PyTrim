import subprocess

def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr