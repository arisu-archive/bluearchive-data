#!/usr/bin/env python3

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path


VERSION_PATTERN = re.compile(r"[A-Za-z0-9._-]+")
SENSITIVE_NAMES = {"id_ed25519", "id_rsa"}
SENSITIVE_SUFFIXES = {".jks", ".key", ".keystore", ".p12", ".pem", ".pfx"}
SERVERS = {
    "global": {
        "package": "com.nexon.bluearchive",
        "key_args": ("keys", "--json", "--server", "asia"),
        "encrypted_dir": "Preload/TableBundles",
        "encrypted": ("Battle.zip", "Excel.zip", "ExcelDB.db", "Module.zip"),
        "plain_dir": "GameData/TableBundles",
        "plain": ("ConquestMap.zip", "HexaMap.zip"),
    },
    "japan": {
        "package": "com.YostarJP.BlueArchive",
        "key_args": ("keys", "--json"),
        "encrypted_dir": "TableBundles",
        "encrypted": (
            "Battle.zip",
            "Excel.zip",
            "ExcelDB.db",
            "Module.zip",
            "ConquestMap.zip",
            "HexaMap.zip",
        ),
        "plain_dir": "",
        "plain": (),
    },
}


def scan_workspace(root: Path, secret: bytes) -> None:
    overlap = max(len(secret) - 1, 0)
    for path in root.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.name.lower() in SENSITIVE_NAMES or path.suffix.lower() in SENSITIVE_SUFFIXES:
            raise ValueError("workspace contains sensitive key material")
        previous = b""
        with path.open("rb") as handle:
            while chunk := handle.read(64 * 1024):
                data = previous + chunk
                if secret in data:
                    raise ValueError("workspace contains sensitive key material")
                previous = data[-overlap:] if overlap else b""


def run_quiet(command: list[str], cwd: Path) -> None:
    try:
        subprocess.run(
            command,
            cwd=cwd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        raise RuntimeError("asset extraction command failed") from None


def main() -> None:
    parser = argparse.ArgumentParser(description="Decrypt downloaded asset bundles")
    parser.add_argument("--server", choices=tuple(SERVERS), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--download-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--assets-dumper", required=True)
    parser.add_argument("--key-tool", required=True)
    args = parser.parse_args()

    if not VERSION_PATTERN.fullmatch(args.version):
        raise ValueError("version has an invalid format")

    config = SERVERS[args.server]
    runner_temp = Path(os.environ["RUNNER_TEMP"])
    with tempfile.TemporaryDirectory(prefix="sqlcipher-key-", dir=runner_temp) as temporary:
        key_path = Path(temporary, "key.pem")
        url = (
            f"https://ba.pokeguy.dev/{config['package']}/decompiled/"
            f"{args.version}/key.pem"
        )
        with urllib.request.urlopen(url, timeout=30) as response:
            public_key = response.read(1024 * 1024 + 1)
        if len(public_key) > 1024 * 1024 or b"-----BEGIN PUBLIC KEY-----" not in public_key:
            raise ValueError("downloaded key is not a valid public-key PEM")
        key_path.write_bytes(public_key)
        key_path.chmod(0o600)

        result = subprocess.run(
            [args.key_tool, *config["key_args"], "--key", str(key_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        sqlcipher_key = json.loads(result.stdout).get("key", "")
        if (
            not isinstance(sqlcipher_key, str)
            or not sqlcipher_key
            or "\n" in sqlcipher_key
            or "\r" in sqlcipher_key
        ):
            raise ValueError("key tool returned an invalid SQLCipher key")
        base64.b64decode(sqlcipher_key, validate=True)
        print(f"::add-mask::{sqlcipher_key}")

        for archive in config["encrypted"]:
            shutil.rmtree(args.output_dir / Path(archive).stem, ignore_errors=True)
            run_quiet(
                [
                    args.assets_dumper,
                    "x",
                    "-s",
                    args.server,
                    "-i",
                    str(args.download_dir / config["encrypted_dir"] / archive),
                    "-o",
                    str(args.output_dir),
                    "-k",
                    sqlcipher_key,
                ],
                args.output_dir,
            )

        for archive in config["plain"]:
            shutil.rmtree(args.output_dir / Path(archive).stem, ignore_errors=True)
            run_quiet(
                [
                    args.assets_dumper,
                    "x",
                    "-s",
                    args.server,
                    "-i",
                    str(args.download_dir / config["plain_dir"] / archive),
                    "-o",
                    str(args.output_dir),
                ],
                args.output_dir,
            )

        scan_workspace(args.output_dir, sqlcipher_key.encode())


if __name__ == "__main__":
    main()
