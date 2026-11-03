import json
import subprocess
from pathlib import Path

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

def get_authorized_users() -> List[str]:
    file_path = Path(".tio.tokens.json")

    if file_path.exists():
        with open(file_path) as token_file:
            tokens = json.load(token_file)
            return [k for k,v in tokens.items()]
    else:
        return []