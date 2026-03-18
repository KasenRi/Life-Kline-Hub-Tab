from __future__ import annotations

import configparser
import hashlib
import json
import logging
import os
import pickle
import random
import shutil
import string
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Generic, TypeVar

import redis as redis_lib
from sqlalchemy import DateTime, Integer, String, Text, create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

ZERO_TIME = "0001-01-01T00:00:00Z"

SYSTEM_APPLICATION = "system_application"
SYSTEM_EMAIL = "system_email"
DISCLAIMER = "disclaimer"
WEB_ABOUT_DESCRIPTION = "web_about_description"
PANEL_PUBLIC_USER_ID = "panel_public_user_id"

VISIT_MODE_LOGIN = 0
VISIT_MODE_PUBLIC = 1

SYSTEM_MONITOR_CPU_INFO = "CPU_INFO"
SYSTEM_MONITOR_MEMORY_INFO = "MEMORY_INFO"
SYSTEM_MONITOR_DISK_INFO = "DISK_INFO"

RAND_CODE_MODE1 = string.ascii_uppercase + string.ascii_lowercase + string.digits
RAND_CODE_MODE2 = string.ascii_lowercase + string.digits


def builtin_asset_root() -> Path:
    return Path(__file__).resolve().parents[1] / "assets"


class MissingSettingError(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def password_encryption(password: str) -> str:
    return md5(md5(md5(password)))


def build_rand_code(count: int, alphabet: str) -> str:
    rng = random.Random(time.time_ns() + random.randint(0, 99))
    return "".join(rng.choice(alphabet or RAND_CODE_MODE1) for _ in range(count))


def format_time(value: datetime | str | None) -> str:
    if value is None:
        return ZERO_TIME
    if isinstance(value, str):
        text = value.replace(" ", "T")
        if text.endswith("+00:00"):
            return f"{text[:-6]}Z"
        return text
    dt = value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.{dt.microsecond:06d}000Z"


def resolve_runtime_path(runtime_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (runtime_root / path).resolve()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    pass


class SoftDeleteModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class User(SoftDeleteModel):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(String(50), default="")
    password: Mapped[str] = mapped_column(String(32), default="")
    name: Mapped[str] = mapped_column(String(20), default="")
    head_image: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[int] = mapped_column(Integer, default=0)
    mail: Mapped[str] = mapped_column(String(50), default="")
    referral_code: Mapped[str] = mapped_column(String(10), default="")
    token: Mapped[str] = mapped_column(String(32), default="")


class SystemSetting(Base):
    __tablename__ = "system_setting"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_name: Mapped[str] = mapped_column(String(50), default="")
    config_value: Mapped[str] = mapped_column(Text, default="")


class ItemIcon(SoftDeleteModel):
    __tablename__ = "item_icon"

    icon_json: Mapped[str] = mapped_column(String(1000), default="")
    title: Mapped[str] = mapped_column(String(50), default="")
    url: Mapped[str] = mapped_column(String(1000), default="")
    lan_url: Mapped[str] = mapped_column(String(1000), default="")
    description: Mapped[str] = mapped_column(String(1000), default="")
    open_method: Mapped[int] = mapped_column(Integer, default=0)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    item_icon_group_id: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[int] = mapped_column(Integer, default=0)


class ItemIconGroup(SoftDeleteModel):
    __tablename__ = "item_icon_group"

    icon: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(String(50), default="")
    description: Mapped[str] = mapped_column(String(1000), default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[int] = mapped_column(Integer, default=0)


class ModuleConfig(SoftDeleteModel):
    __tablename__ = "module_config"

    user_id: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(255), default="")
    value_json: Mapped[str] = mapped_column(Text, default="")


class File(SoftDeleteModel):
    __tablename__ = "file"

    src: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[int] = mapped_column(Integer, default=0)
    file_name: Mapped[str] = mapped_column(Text, default="")
    method: Mapped[int] = mapped_column(Integer, default=0)
    ext: Mapped[str] = mapped_column(Text, default="")


class UserConfig(Base):
    __tablename__ = "user_config"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    panel_json: Mapped[str] = mapped_column(Text, default="")
    search_engine_json: Mapped[str] = mapped_column(Text, default="")


@event.listens_for(Base, "before_insert", propagate=True)
def before_insert(_: Any, __: Any, target: Any) -> None:
    now = utcnow()
    if hasattr(target, "created_at") and getattr(target, "created_at", None) is None:
        target.created_at = now
    if hasattr(target, "updated_at"):
        target.updated_at = now


@event.listens_for(Base, "before_update", propagate=True)
def before_update(_: Any, __: Any, target: Any) -> None:
    if hasattr(target, "updated_at"):
        target.updated_at = utcnow()


@dataclass(slots=True)
class VersionInfo:
    version_code: int
    version: str


@dataclass(slots=True)
class UserSnapshot:
    id: int
    created_at: datetime | None
    updated_at: datetime | None
    username: str
    password: str
    name: str
    head_image: str
    status: int
    role: int
    mail: str
    referral_code: str
    token: str


T = TypeVar("T")


class CacheProtocol(Generic[T]):
    def set(self, key: str, value: T, duration: timedelta | None) -> None:
        raise NotImplementedError

    def get(self, key: str) -> tuple[T | None, bool]:
        raise NotImplementedError

    def set_default(self, key: str, value: T) -> None:
        raise NotImplementedError

    def set_keep_expiration(self, key: str, value: T) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def item_count(self) -> int:
        raise NotImplementedError

    def flush(self) -> None:
        raise NotImplementedError


class MemoryCache(CacheProtocol[T]):
    def __init__(self, default_expiration: timedelta, cleanup_interval: timedelta | None) -> None:
        self.default_expiration = default_expiration
        self.cleanup_interval = cleanup_interval
        self._values: dict[str, tuple[T, float | None]] = {}
        self._lock = threading.RLock()
        if cleanup_interval and cleanup_interval.total_seconds() > 0:
            thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            thread.start()

    def _cleanup_loop(self) -> None:
        interval = max(self.cleanup_interval.total_seconds(), 1) if self.cleanup_interval else 1
        while True:
            time.sleep(interval)
            self._purge_expired()

    def _purge_expired(self) -> None:
        now = time.time()
        with self._lock:
            expired = [key for key, (_, exp) in self._values.items() if exp is not None and exp <= now]
            for key in expired:
                self._values.pop(key, None)

    def _expiration(self, duration: timedelta | None) -> float | None:
        if duration is None or duration.total_seconds() <= 0:
            return None
        return time.time() + duration.total_seconds()

    def set(self, key: str, value: T, duration: timedelta | None) -> None:
        with self._lock:
            self._values[key] = (value, self._expiration(duration))

    def get(self, key: str) -> tuple[T | None, bool]:
        with self._lock:
            item = self._values.get(key)
            if item is None:
                return None, False
            value, expiration = item
            if expiration is not None and expiration <= time.time():
                self._values.pop(key, None)
                return None, False
            return value, True

    def set_default(self, key: str, value: T) -> None:
        self.set(key, value, self.default_expiration)

    def set_keep_expiration(self, key: str, value: T) -> None:
        with self._lock:
            item = self._values.get(key)
            if item is None:
                self._values[key] = (value, self._expiration(self.default_expiration))
                return
            _, expiration = item
            if expiration is not None and expiration <= time.time():
                self._values[key] = (value, self._expiration(self.default_expiration))
                return
            self._values[key] = (value, expiration if expiration is not None else self._expiration(self.default_expiration))

    def delete(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)

    def item_count(self) -> int:
        self._purge_expired()
        return len(self._values)

    def flush(self) -> None:
        with self._lock:
            self._values.clear()


class RedisCache(CacheProtocol[T]):
    def __init__(self, client: redis_lib.Redis, hash_key: str, default_expiration: timedelta) -> None:
        self.client = client
        self.hash_key = hash_key
        self.default_expiration = default_expiration

    def _encode(self, value: T, duration: timedelta | None) -> bytes:
        expiration = None
        if duration is not None and duration.total_seconds() > 0:
            expiration = time.time() + duration.total_seconds()
        return pickle.dumps((expiration, value))

    def _decode(self, raw: bytes) -> tuple[T | None, bool, float | None]:
        expiration, value = pickle.loads(raw)
        if expiration is not None and expiration <= time.time():
            return None, False, expiration
        return value, True, expiration

    def set(self, key: str, value: T, duration: timedelta | None) -> None:
        self.client.hset(self.hash_key, key, self._encode(value, duration))

    def get(self, key: str) -> tuple[T | None, bool]:
        raw = self.client.hget(self.hash_key, key)
        if raw is None:
            return None, False
        value, ok, _ = self._decode(raw)
        if not ok:
            self.delete(key)
            return None, False
        return value, True

    def set_default(self, key: str, value: T) -> None:
        self.set(key, value, self.default_expiration)

    def set_keep_expiration(self, key: str, value: T) -> None:
        raw = self.client.hget(self.hash_key, key)
        if raw is None:
            self.set_default(key, value)
            return
        decoded, ok, expiration = self._decode(raw)
        if not ok:
            self.set_default(key, value)
            return
        _ = decoded
        duration = None
        if expiration is not None:
            duration = timedelta(seconds=max(expiration - time.time(), 0))
        self.set(key, value, duration if duration and duration.total_seconds() > 0 else self.default_expiration)

    def delete(self, key: str) -> None:
        self.client.hdel(self.hash_key, key)

    def item_count(self) -> int:
        return int(self.client.hlen(self.hash_key))

    def flush(self) -> None:
        self.client.delete(self.hash_key)


class IniConfig:
    def __init__(self, filename: Path) -> None:
        self.filename = filename
        self.parser = configparser.ConfigParser()
        self.parser.read(filename, encoding="utf-8")
        self.default = {
            "base": {
                "http_port": "9090",
                "source_path": "./files",
                "source_temp_path": "./files/temp",
            },
            "sqlite": {
                "file_path": "./database.db",
            },
        }

    def get_value_string(self, section: str, name: str) -> str:
        return self.parser.get(section, name, fallback="")

    def get_value_string_or_default(self, section: str, name: str) -> str:
        value = self.get_value_string(section, name)
        if value:
            return value
        return self.default.get(section, {}).get(name, "")

    def get_value_int(self, section: str, name: str) -> int:
        value = self.get_value_string(section, name)
        try:
            return int(value)
        except ValueError:
            return 0

    def get_section(self, section: str) -> dict[str, str]:
        if not self.parser.has_section(section):
            raise KeyError(section)
        return {key: value for key, value in self.parser.items(section)}


class SystemSettingCache:
    def __init__(self, ctx: "AppContext", cache: CacheProtocol[Any]) -> None:
        self.ctx = ctx
        self.cache = cache

    def get_value_string(self, config_name: str) -> str:
        cached, ok = self.cache.get(config_name)
        if ok and isinstance(cached, str):
            return cached
        with self.ctx.session() as session:
            setting = session.scalar(select(SystemSetting).where(SystemSetting.config_name == config_name))
            if setting is None:
                raise MissingSettingError("no exists")
            self.cache.set_default(config_name, setting.config_value or "")
            return setting.config_value or ""

    def get_value_by_interface(self, config_name: str) -> Any:
        value = self.get_value_string(config_name)
        return json.loads(value)

    def set(self, config_name: str, config_value: Any) -> None:
        self.cache.delete(config_name)
        stored = config_value if isinstance(config_value, str) else json.dumps(config_value, ensure_ascii=False)
        with self.ctx.session() as session:
            setting = session.scalar(select(SystemSetting).where(SystemSetting.config_name == config_name))
            if setting is None:
                session.add(SystemSetting(config_name=config_name, config_value=stored))
            else:
                setting.config_value = stored
            session.commit()


@dataclass(slots=True)
class AppContext:
    runtime_root: Path
    asset_root: Path
    logger: logging.Logger
    config: IniConfig
    version_info: VersionInfo
    engine: Engine
    session_factory: sessionmaker[Session]
    user_token: CacheProtocol[UserSnapshot]
    c_user_token: CacheProtocol[str]
    verify_code_cache: CacheProtocol[str]
    system_monitor: CacheProtocol[Any]
    system_setting: SystemSettingCache
    redis_client: redis_lib.Redis | None

    @classmethod
    def initialize(cls, runtime_root: Path) -> "AppContext":
        asset_root = builtin_asset_root()
        logger = init_logger(runtime_root)
        ensure_asset_copy(asset_root / "conf.example.ini", runtime_root / "conf" / "conf.example.ini")
        conf_file = runtime_root / "conf" / "conf.ini"
        if not conf_file.exists():
            ensure_asset_copy(asset_root / "conf.example.ini", conf_file)
        ensure_language_files(asset_root, runtime_root, logger)
        config = IniConfig(conf_file)
        version_info = read_version_info(asset_root)

        redis_client: redis_lib.Redis | None = None
        if config.get_value_string("base", "cache_drive") == "redis" or config.get_value_string("base", "queue_drive") == "redis":
            redis_cfg = config.get_section("redis")
            redis_client = redis_lib.Redis(
                host=redis_cfg.get("address", "127.0.0.1").split(":")[0],
                port=int(redis_cfg.get("address", "127.0.0.1:6379").split(":")[1]),
                password=redis_cfg.get("password", "") or None,
                db=int(redis_cfg.get("db", "0")),
                decode_responses=False,
            )

        engine = build_engine(runtime_root, config)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
        Base.metadata.create_all(
            engine,
            tables=[
                User.__table__,
                SystemSetting.__table__,
                ItemIcon.__table__,
                UserConfig.__table__,
                File.__table__,
                ItemIconGroup.__table__,
                ModuleConfig.__table__,
            ],
        )

        ctx_placeholder = cls(
            runtime_root=runtime_root,
            asset_root=asset_root,
            logger=logger,
            config=config,
            version_info=version_info,
            engine=engine,
            session_factory=session_factory,
            user_token=MemoryCache[UserSnapshot](timedelta(minutes=1), timedelta(hours=1)),
            c_user_token=MemoryCache[str](timedelta(hours=72), timedelta(hours=48)),
            verify_code_cache=MemoryCache[str](timedelta(minutes=10), timedelta(minutes=10)),
            system_monitor=MemoryCache[Any](timedelta(hours=5), None),
            system_setting=None,  # type: ignore[arg-type]
            redis_client=redis_client,
        )

        ctx_placeholder.user_token = ctx_placeholder.new_cache("UserToken", timedelta(minutes=1), timedelta(hours=1))
        ctx_placeholder.c_user_token = ctx_placeholder.new_cache("CUserToken", timedelta(hours=72), timedelta(hours=48))
        ctx_placeholder.verify_code_cache = ctx_placeholder.new_cache("VerifyCodeCachePool", timedelta(minutes=10), timedelta(minutes=10))
        system_setting_cache = ctx_placeholder.new_cache("systemSettingCache", timedelta(hours=5), None)
        ctx_placeholder.system_monitor = ctx_placeholder.new_cache("systemMonitorCache", timedelta(hours=5), None)
        ctx_placeholder.system_setting = SystemSettingCache(ctx_placeholder, system_setting_cache)

        not_found_and_create_user(ctx_placeholder)
        return ctx_placeholder

    def new_cache(self, name: str, default_expiration: timedelta, cleanup_interval: timedelta | None) -> CacheProtocol[Any]:
        drive = self.config.get_value_string("base", "cache_drive") or "memory"
        self.logger.debug("缓存驱动: %s", drive)
        if drive == "redis":
            redis_cfg = self.config.get_section("redis")
            prefix = redis_cfg.get("prefix", "")
            if self.redis_client is None:
                raise RuntimeError("redis cache requested but redis client is not initialized")
            return RedisCache(self.redis_client, prefix + name, default_expiration)
        return MemoryCache(default_expiration, cleanup_interval)

    def session(self) -> Session:
        return self.session_factory()

    @property
    def http_port(self) -> int:
        return int(self.config.get_value_string_or_default("base", "http_port"))

    @property
    def source_path(self) -> Path:
        return resolve_runtime_path(self.runtime_root, self.config.get_value_string("base", "source_path") or "./uploads")

    @property
    def source_path_raw(self) -> str:
        return self.config.get_value_string("base", "source_path") or "./uploads"

    @property
    def web_path(self) -> Path:
        return self.runtime_root / "web"


def init_logger(runtime_root: Path) -> logging.Logger:
    log_path = runtime_root / "runtime" / "runlog" / "running.log"
    ensure_parent(log_path)
    logger_name = f"sun_panel_python.{runtime_root}"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%dT%H:%M:%S")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def ensure_asset_copy(source: Path, target: Path) -> None:
    if target.exists():
        return
    ensure_parent(target)
    shutil.copyfile(source, target)


def ensure_language_files(asset_root: Path, runtime_root: Path, logger: logging.Logger) -> None:
    for name in ("zh-cn.ini", "en-us.ini"):
        source = asset_root / "lang" / name
        target = runtime_root / "lang" / name
        if not target.exists():
            logger.info("输出语言文件: lang/%s", name)
            ensure_asset_copy(source, target)


def read_version_info(asset_root: Path) -> VersionInfo:
    version_raw = (asset_root / "version").read_text(encoding="utf-8").strip()
    version_code, version = version_raw.split("|", 1)
    return VersionInfo(version_code=int(version_code), version=version)


def build_engine(runtime_root: Path, config: IniConfig) -> Engine:
    driver = config.get_value_string_or_default("base", "database_drive") or "sqlite"
    if driver == "mysql":
        mysql_cfg = config.get_section("mysql")
        wait_timeout = int(mysql_cfg.get("wait_timeout", "100") or "100")
        username = mysql_cfg.get("username", "root")
        password = mysql_cfg.get("password", "root")
        host = mysql_cfg.get("host", "127.0.0.1")
        port = mysql_cfg.get("port", "3306")
        database = mysql_cfg.get("db_name", "sun_panel")
        return create_engine(
            f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4",
            pool_recycle=wait_timeout,
            future=True,
        )

    db_path = resolve_runtime_path(runtime_root, config.get_value_string_or_default("sqlite", "file_path"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", future=True)


def not_found_and_create_user(ctx: AppContext) -> None:
    with ctx.session() as session:
        user = session.scalar(select(User).where(User.deleted_at.is_(None)).order_by(User.id.asc()))
        if user is not None:
            return
        username = "admin@sun.cc"
        session.add(
            User(
                username=username,
                password=password_encryption("12345678"),
                name=username,
                status=1,
                role=1,
                mail=username,
            )
        )
        session.commit()


def user_to_snapshot(user: User) -> UserSnapshot:
    return UserSnapshot(
        id=user.id,
        created_at=user.created_at,
        updated_at=user.updated_at,
        username=user.username or "",
        password=user.password or "",
        name=user.name or "",
        head_image=user.head_image or "",
        status=user.status or 0,
        role=user.role or 0,
        mail=user.mail or "",
        referral_code=user.referral_code or "",
        token=user.token or "",
    )


def serialize_zero_user() -> dict[str, Any]:
    return {
        "ID": 0,
        "CreatedAt": ZERO_TIME,
        "UpdatedAt": ZERO_TIME,
        "DeletedAt": None,
        "id": 0,
        "createTime": ZERO_TIME,
        "updateTime": ZERO_TIME,
        "username": "",
        "password": "",
        "name": "",
        "headImage": "",
        "status": 0,
        "role": 0,
        "mail": "",
        "referralCode": "",
        "token": "",
        "userId": 0,
    }


def serialize_user(snapshot: UserSnapshot, *, password: str | None = None, token: str | None = None) -> dict[str, Any]:
    return {
        "ID": 0,
        "CreatedAt": ZERO_TIME,
        "UpdatedAt": ZERO_TIME,
        "DeletedAt": None,
        "id": snapshot.id,
        "createTime": format_time(snapshot.created_at),
        "updateTime": format_time(snapshot.updated_at),
        "username": snapshot.username,
        "password": snapshot.password if password is None else password,
        "name": snapshot.name,
        "headImage": snapshot.head_image,
        "status": snapshot.status,
        "role": snapshot.role,
        "mail": snapshot.mail,
        "referralCode": snapshot.referral_code,
        "token": snapshot.token if token is None else token,
        "userId": 0,
    }


def serialize_auth_user(snapshot: UserSnapshot) -> dict[str, Any]:
    payload = serialize_zero_user()
    payload.update(
        {
            "id": snapshot.id,
            "username": snapshot.username,
            "name": snapshot.name,
            "headImage": snapshot.head_image,
            "role": snapshot.role,
        }
    )
    return payload


def serialize_item_icon_group(group: ItemIconGroup) -> dict[str, Any]:
    return {
        "ID": 0,
        "CreatedAt": ZERO_TIME,
        "UpdatedAt": ZERO_TIME,
        "DeletedAt": None,
        "id": group.id,
        "createTime": format_time(group.created_at),
        "updateTime": format_time(group.updated_at),
        "icon": group.icon or "",
        "title": group.title or "",
        "description": group.description or "",
        "sort": group.sort or 0,
        "userId": group.user_id or 0,
        "user": serialize_zero_user(),
    }


def serialize_item_icon(icon: ItemIcon) -> dict[str, Any]:
    icon_value: Any = None
    if icon.icon_json:
        try:
            icon_value = json.loads(icon.icon_json)
        except json.JSONDecodeError:
            icon_value = None
    return {
        "ID": 0,
        "CreatedAt": ZERO_TIME,
        "UpdatedAt": ZERO_TIME,
        "DeletedAt": None,
        "id": icon.id,
        "createTime": format_time(icon.created_at),
        "updateTime": format_time(icon.updated_at),
        "icon": icon_value,
        "title": icon.title or "",
        "url": icon.url or "",
        "lanUrl": icon.lan_url or "",
        "description": icon.description or "",
        "openMethod": icon.open_method or 0,
        "sort": icon.sort or 0,
        "itemIconGroupId": icon.item_icon_group_id or 0,
        "userId": icon.user_id or 0,
        "user": serialize_zero_user(),
    }


def serialize_user_config(config: UserConfig) -> dict[str, Any]:
    panel: Any = None
    search_engine: Any = None
    if config.panel_json:
        try:
            panel = json.loads(config.panel_json)
        except json.JSONDecodeError:
            panel = None
    if config.search_engine_json:
        try:
            search_engine = json.loads(config.search_engine_json)
        except json.JSONDecodeError:
            search_engine = None
    return {
        "userId": config.user_id,
        "panel": panel,
        "searchEngine": search_engine,
    }
