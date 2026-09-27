"""Download an Ashu local model file without hardcoding a specific provider URL.

Example:
    python scripts/download_model.py \
      --url "<MODEL_FILE_URL>" \
      --output models/ashu-model.gguf

An optional sha256 can be supplied for integrity verification.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sha256")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading model to {output} ...")
    try:
        urllib.request.urlretrieve(args.url, output)
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    if args.sha256:
        actual = sha256(output)
        if actual.lower() != args.sha256.lower():
            print(f"SHA256 mismatch: expected {args.sha256}, got {actual}", file=sys.stderr)
            output.unlink(missing_ok=True)
            return 2
        print("SHA256 verified.")

    print(f"Model ready: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
