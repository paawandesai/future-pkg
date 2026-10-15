"""Fetch the assessment inputs at a pinned commit and verify their checksums.

The files are not committed: the source repository has no license. Usage: python scripts/fetch_data.py [dest]
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

COMMIT = "4b8c67246a659c26bd222079c5c7829d295acad9"
BASE = f"https://raw.githubusercontent.com/future-research/candidate-assessment/{COMMIT}/data"
FILES = {
    "exercises.json": "ffdcf6b3b51787d1f14b327ee9d31b9b1f8ee469eaa11068180f056ce5118798",
    "member-context.json": "c2e6373eaeb10c889d06e46b5ceb7a5f5a5df463d68198dc615d2ee9099675d2",
}


def main() -> int:
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
    dest.mkdir(parents=True, exist_ok=True)
    for name, sha in FILES.items():
        target = dest / name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == sha:
            continue
        with urllib.request.urlopen(f"{BASE}/{name}", timeout=30) as resp:  # noqa: S310 (fixed https URL)
            body = resp.read()
        if hashlib.sha256(body).hexdigest() != sha:
            print(f"checksum mismatch for {name}", file=sys.stderr)
            return 1
        target.write_bytes(body)
    print(f"data ready at {COMMIT[:7]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
