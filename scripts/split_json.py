#!/usr/bin/env python3

import argparse
import json
import tempfile
from pathlib import Path
from textwrap import indent

DOCUMENT_PREFIX = '{\n  "data_list": [\n'
DOCUMENT_SUFFIX = "\n  ]\n}\n"
ITEM_SEPARATOR = ",\n"
ITEM_INDENT = "    "


def render_item(item: object) -> str:
    """Render one data_list element as it appears inside the split document."""
    return indent(json.dumps(item, indent=2), ITEM_INDENT)


def render_document(rendered: list[str]) -> str:
    return DOCUMENT_PREFIX + ITEM_SEPARATOR.join(rendered) + DOCUMENT_SUFFIX


def split_file(source: Path, max_bytes: int) -> list[Path]:
    if max_bytes < 1:
        raise ValueError("maximum chunk size must be positive")
    document = json.loads(source.read_text(encoding="utf-8"))
    items = document.get("data_list")
    if not isinstance(items, list) or not items:
        raise ValueError("input must contain a non-empty data_list array")

    # json.dumps escapes non-ASCII by default, so a rendered length in characters
    # equals its UTF-8 byte count. Chunk sizing below relies on that equality.
    overhead = len(DOCUMENT_PREFIX) + len(DOCUMENT_SUFFIX)
    target = max(max_bytes * 80 // 100, 1)
    chunks: list[list[str]] = []
    current: list[str] = []
    current_size = overhead
    for index, item in enumerate(items):
        rendered = render_item(item)
        item_size = len(rendered) + (len(ITEM_SEPARATOR) if current else 0)
        if not current and overhead + len(rendered) > max_bytes:
            raise ValueError(
                f"{source}: data_list item {index} does not fit in a chunk of "
                f"{max_bytes} bytes"
            )
        if current and current_size + item_size > target:
            chunks.append(current)
            current = []
            current_size = overhead
            item_size = len(rendered)
        current.append(rendered)
        current_size += item_size
    chunks.append(current)

    outputs: list[Path] = []
    try:
        for index, chunk in enumerate(chunks):
            output = source.with_name(f"{source.stem}_{index}.json")
            with tempfile.NamedTemporaryFile(
                "w", dir=source.parent, encoding="utf-8", delete=False, newline="\n"
            ) as temporary:
                temporary.write(render_document(chunk))
            Path(temporary.name).replace(output)
            outputs.append(output)
            written = output.stat().st_size
            if written > max_bytes:
                raise ValueError(
                    f"{output}: chunk is {written} bytes, above the {max_bytes} byte limit"
                )
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
