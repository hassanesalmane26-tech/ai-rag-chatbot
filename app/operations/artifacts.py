"""Create a deterministic manifest for an already-built frontend artifact."""

import argparse
import hashlib
import json
from pathlib import Path


def artifact_manifest(root: Path) -> dict:
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        content = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    if not files:
        raise ValueError("Artifact directory is empty")
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return {"format": "trident-artifact-manifest-v1", "files": files, "sha256": hashlib.sha256(canonical).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(artifact_manifest(args.root), sort_keys=True))


if __name__ == "__main__":
    main()
