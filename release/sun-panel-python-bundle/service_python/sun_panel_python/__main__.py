from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import select

from .app import run
from .runtime import AppContext, User, builtin_asset_root, ensure_asset_copy, password_encryption, read_version_info


def logo(runtime_root: Path) -> None:
    asset_root = builtin_asset_root()
    version_info = read_version_info(asset_root)
    print("     ____            ___                __")
    print("    / __/_ _____    / _ \\___ ____  ___ / /")
    print("   _\\ \\/ // / _ \\  / ___/ _ `/ _ \\/ -_) / ")
    print("  /___/\\_,_/_//_/ /_/   \\_,_/_//_/\\__/_/  ")
    print("")
    print(f"Version: {version_info.version}")
    print("Welcome to the Sun-Panel.")
    print("Project address: https://github.com/hslr-s/sun-panel")


def generate_config(runtime_root: Path) -> None:
    asset_root = builtin_asset_root()
    ensure_asset_copy(asset_root / "conf.example.ini", runtime_root / "conf" / "conf.example.ini")
    ensure_asset_copy(asset_root / "conf.example.ini", runtime_root / "conf" / "conf.ini")
    print("Generating configuration file")
    print("The configuration file has been created  conf/conf.ini  Please modify according to your own needs")


def password_reset(runtime_root: Path) -> None:
    ctx = AppContext.initialize(runtime_root)
    with ctx.session() as session:
        user = session.scalar(select(User).where(User.deleted_at.is_(None), User.role == 1).order_by(User.id.asc()))
        if user is None:
            print("ERROR no admin user")
            return
        user.password = password_encryption("12345678")
        user.token = ""
        session.commit()
        print("The password has been successfully reset. Here is the account information")
        print("Username ", user.username)
        print("Password ", "12345678")


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-config", action="store_true", dest="config")
    parser.add_argument("-password-reset", action="store_true", dest="password_reset")
    args = parser.parse_args()

    runtime_root = Path.cwd()
    logo(runtime_root)

    if args.config:
        generate_config(runtime_root)
        return
    if args.password_reset:
        password_reset(runtime_root)
        return

    ctx = AppContext.initialize(runtime_root)
    run(ctx)


if __name__ == "__main__":
    main()
