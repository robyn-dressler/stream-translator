import subprocess

from typing import List

def run_command(cmd: List[str], error_message: str, background_process=False, shell=False, cwd=None):
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        shell=shell,
        cwd=cwd
    )

    if not background_process and p.wait() != 0:
        raise RuntimeError(error_message)

    return p