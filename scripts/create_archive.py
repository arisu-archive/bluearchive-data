#!/usr/bin/env python3

import argparse
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def create_zip(root: Path, destination: Path, files: list[str]) -> None:
    root = root.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(dir=destination.parent, delete=False)
    temporary.close()
    temporary_path = Path(temporary.name)

    try:
        with zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(set(files)):
                relative = PurePosixPath(name)
                if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                    raise ValueError("git returned an unsafe archive path")
                source = root.joinpath(*relative.parts)
                if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(root):
                    raise ValueError("archive input is not a safe regular file")
                archive.write(source, relative.as_posix())
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def git_files(root: Path) -> list[str]:
    files: list[str] = []
    for command in (("git", "ls-files", "-z"), ("git", "ls-files", "--others", "--exclude-standard", "-z")):
        output = subprocess.run(command, cwd=root, check=True, capture_output=True).stdout
        files.extend(os.fsdecode(name) for name in output.split(b"\0") if name)
    if not files:
        raise ValueError("workspace contains no files to archive")
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive tracked and untracked asset files")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    create_zip(args.root, args.output, git_files(args.root))


if __name__ == "__main__":
    main()
