from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .runtime import builtin_asset_root, ensure_asset_copy


def sync_web(dist_dir: Path, runtime_root: Path) -> Path:
    if not dist_dir.exists():
        raise FileNotFoundError(f"dist directory not found: {dist_dir}")
    target = runtime_root / "web"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(dist_dir, target)
    custom_dir = target / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("index.js", "index.css"):
        file_path = custom_dir / filename
        if not file_path.exists():
            file_path.write_text("", encoding="utf-8")
    return target


def prepare_runtime(runtime_root: Path, dist_dir: Path | None = None) -> None:
    asset_root = builtin_asset_root()
    ensure_asset_copy(asset_root / "conf.example.ini", runtime_root / "conf" / "conf.example.ini")
    ensure_asset_copy(asset_root / "conf.example.ini", runtime_root / "conf" / "conf.ini")
    if dist_dir is not None:
        sync_web(dist_dir, runtime_root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", default=".", help="runtime root directory")
    parser.add_argument("--dist", default=None, help="frontend dist directory to copy into runtime web/")
    args = parser.parse_args()

    runtime_root = Path(args.runtime).resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    dist_dir = Path(args.dist).resolve() if args.dist else None
    prepare_runtime(runtime_root, dist_dir)

    print(f"runtime prepared: {runtime_root}")
    if dist_dir is not None:
        print(f"web synced from: {dist_dir}")


if __name__ == "__main__":
    main()
