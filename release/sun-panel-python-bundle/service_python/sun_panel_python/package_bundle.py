from __future__ import annotations

import argparse
import shutil
import tarfile
from pathlib import Path

from .prepare_runtime import prepare_runtime
from .runtime import builtin_asset_root, ensure_asset_copy


def write_file(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def create_bundle(repo_root: Path, output_dir: Path) -> tuple[Path, Path]:
    bundle_root = output_dir / "sun-panel-python-bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)

    dist_dir = repo_root / "dist"
    if not dist_dir.exists():
        raise FileNotFoundError(f"frontend dist not found: {dist_dir}. run frontend build first")

    service_python_root = repo_root / "service_python"
    bundle_service_root = bundle_root / "service_python"

    for relative in [
        "pyproject.toml",
        "uv.lock",
        "README.md",
        ".gitignore",
        "assets",
        "sun_panel_python",
    ]:
        source = service_python_root / relative
        target = bundle_service_root / relative
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".venv"))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    prepare_runtime(bundle_root, dist_dir)

    asset_root = builtin_asset_root()
    ensure_asset_copy(asset_root / "conf.example.ini", bundle_root / "conf" / "conf.example.ini")
    ensure_asset_copy(asset_root / "conf.example.ini", bundle_root / "conf" / "conf.ini")

    write_file(
        bundle_root / "install.sh",
        """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --user uv
  export PATH="$HOME/.local/bin:$PATH"
fi

PYTHONPATH=./service_python uv sync --project service_python --locked
echo "Dependencies installed."
""",
        executable=True,
    )

    write_file(
        bundle_root / "run.sh",
        """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x "./service_python/.venv/bin/python" ]; then
  ./install.sh
fi

PYTHONPATH=./service_python uv run --project service_python python -m sun_panel_python
""",
        executable=True,
    )

    write_file(
        bundle_root / "README_DEPLOY.txt",
        """Sun-Panel Python Bundle

Files:
- web/                built frontend
- service_python/     self-contained Python backend project
- conf/conf.ini       default config
- install.sh          install Python dependencies with uv
- run.sh              start backend on port 3002

Run on another Linux machine:
1. copy this whole folder to the target machine
2. cd into the folder
3. ./install.sh
4. ./run.sh
5. open http://127.0.0.1:3002 or http://<server-ip>:3002

Default admin account:
- username: admin@sun.cc
- password: 12345678

Requirements:
- python3
- network access for dependency installation, unless you already have the needed Python packages cached
""",
    )

    archive_path = output_dir / "sun-panel-python-bundle.tar.gz"
    if archive_path.exists():
        archive_path.unlink()
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(bundle_root, arcname=bundle_root.name)
    return bundle_root, archive_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", help="repository root")
    parser.add_argument("--output", default="release", help="output directory")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle_root, archive_path = create_bundle(repo_root, output_dir)
    print(f"bundle directory: {bundle_root}")
    print(f"bundle archive: {archive_path}")


if __name__ == "__main__":
    main()
