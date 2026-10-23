import json
import time
from pathlib import Path
from typing import Any


def load_json(file_path: str | Path) -> Any:
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def format_options(data: dict[str, str]) -> str:
    return "\n".join(f'- "{key}"' for key in data)


def get_elapsed_ms(start_time: float) -> float:
    return (time.perf_counter() - start_time) * 1000
