#!/usr/bin/env python3

import argparse
import json
import tempfile
from pathlib import Path


def split_file(source: Path, max_bytes: int) -> list[Path]:
    if max_bytes < 1:
        raise ValueError("maximum chunk size must be positive")
    document = json.loads(source.read_text(encoding="utf-8"))
    items = document.get("data_list")
    if not isinstance(items, list) or not items:
        raise ValueError("input must contain a non-empty data_list array")

    target = max(max_bytes * 80 // 100, 1)
    chunks: list[list[object]] = []
    current: list[object] = []
    current_size = 0
    for item in items:
        item_size = len(json.dumps(item, separators=(",", ":")).encode()) + 1
        if current and current_size + item_size > target:
            chunks.append(current)
            current = []
            current_size = 0
        current.append(item)
        current_size += item_size
    chunks.append(current)

    outputs: list[Path] = []
    try:
        for index, chunk in enumerate(chunks):
            output = source.with_name(f"{source.stem}_{index}.json")
            with tempfile.NamedTemporaryFile(
                "w", dir=source.parent, encoding="utf-8", delete=False
            ) as temporary:
                json.dump({"data_list": chunk}, temporary, indent=2)
                temporary.write("\n")
            Path(temporary.name).replace(output)
            outputs.append(output)
    except Exception:
        for output in outputs:
            output.unlink(missing_ok=True)
        raise
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Split oversized asset JSON files")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--threshold-mib", type=int, default=50)
    parser.add_argument("--chunk-mib", type=int, default=100)
    args = parser.parse_args()

    threshold = args.threshold_mib * 1024 * 1024
    max_bytes = args.chunk_mib * 1024 * 1024
    oversized = [
        source
        for source in args.root.rglob("*.json")
        if ".git" not in source.parts and source.stat().st_size > threshold
    ]
    for source in oversized:
        split_file(source, max_bytes)
        source.unlink()


if __name__ == "__main__":
    main()
