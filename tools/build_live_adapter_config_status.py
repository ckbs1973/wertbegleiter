#!/usr/bin/env python3
"""Write live adapter configuration readiness for the frontend."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_freaks.live_config import adapter_config_status_from_env_file


DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_OUTPUT_PATH = ROOT / "frontend" / "public" / "data" / "live_adapter_config_status.json"


def write_config_status(env_file: Path = DEFAULT_ENV_PATH, output_file: Path = DEFAULT_OUTPUT_PATH) -> dict[str, object]:
    payload = adapter_config_status_from_env_file(env_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    payload = write_config_status(args.env_file, args.output_file)
    print(
        f"configured={payload['configured_count']}/4 "
        f"env_exists={payload['env_file']['exists']} "
        f"output={args.output_file}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
