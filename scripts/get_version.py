#!/usr/bin/env python3

import argparse
import os
import re
import subprocess
from pathlib import Path


VERSION_PATTERN = re.compile(r"[A-Za-z0-9._-]+")


def should_skip(latest: str, current: str | None, force_update: bool) -> bool:
    if not VERSION_PATTERN.fullmatch(latest):
        raise ValueError("latest version has an invalid format")
    return not force_update and current == latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Determine whether server assets changed")
    parser.add_argument("--server", choices=("global", "japan"), required=True)
    parser.add_argument("--current-file", type=Path, required=True)
    parser.add_argument("--force-update", choices=("true", "false"), required=True)
    parser.add_argument("--assets-dumper", default="assets-dumper")
    args = parser.parse_args()

    result = subprocess.run(
        [args.assets_dumper, "version", "-s", args.server],
        check=True,
        capture_output=True,
        text=True,
    )
    latest = result.stdout.strip()
    outputs = Path(os.environ["GITHUB_OUTPUT"])

    if not latest:
        outputs.open("a", encoding="utf-8").write("skip=true\n")
        return

    current = args.current_file.read_text(encoding="utf-8") if args.current_file.exists() else None
    skip = should_skip(latest, current, args.force_update == "true")
    with outputs.open("a", encoding="utf-8") as output:
        output.write(f"version={latest}\n")
        output.write(f"skip={str(skip).lower()}\n")
    print(f"::notice title=Latest Resources Version::{latest}")


if __name__ == "__main__":
    main()
