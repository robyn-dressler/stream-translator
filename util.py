import json
import logging
import subprocess
from io import TextIOWrapper
from pathlib import Path

from typing import List, Mapping


def run_command(cmd: List[str], error_message: str, background_process=False, env: Mapping[str, str] | None = None) -> subprocess.Popen:
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        env=env,
    )

    if not background_process and p.wait() != 0:
        raise RuntimeError(error_message)

    return p

def overwrite_file(file: TextIOWrapper, text: str):
    file.seek(0)
    file.write(text)
    file.truncate()
    file.flush()

def get_authorized_users() -> List[str]:
    file_path = Path(".tio.tokens.json")

    if file_path.exists():
        with open(file_path) as token_file:
            tokens = json.load(token_file)
            return [k for k,v in tokens.items()]
    else:
        return []

def get_twitch_id_map() -> Mapping[str, str]:
    file_path = Path("twitch_ids.json")
    if file_path.exists():
        with open(file_path) as f:
            return json.load(f)

    raise RuntimeError("No twitch_ids.json found")