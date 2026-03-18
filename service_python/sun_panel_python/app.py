from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import psutil
import uvicorn
from bs4 import BeautifulSoup
from fastapi import Depends, FastAPI, File as FastAPIFile, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text

from .runtime import (
    DISCLAIMER,
    PANEL_PUBLIC_USER_ID,
    SYSTEM_MONITOR_CPU_INFO,
    SYSTEM_MONITOR_DISK_INFO,
    SYSTEM_MONITOR_MEMORY_INFO,
    VISIT_MODE_LOGIN,
    VISIT_MODE_PUBLIC,
    WEB_ABOUT_DESCRIPTION,
    AppContext,
    File,
    ItemIcon,
    ItemIconGroup,
    MissingSettingError,
    ModuleConfig,
    User,
    UserConfig,
    ZERO_TIME,
    build_rand_code,
    format_time,
    md5,
    password_encryption,
    serialize_auth_user,
    serialize_item_icon,
    serialize_item_icon_group,
    serialize_user,
    serialize_user_config,
    serialize_zero_user,
    user_to_snapshot,
    utcnow,
)

ERROR_MESSAGES = {
    1000: "Not logged in yet",
    1003: "Incorrect username or password",
    1004: "Account disabled or not activated",
    1005: "No current permission for operation",
    1006: "Account does not exist",
    1007: "Old password error",
    1200: "Database error",
    1201: "Please keep at least one",
    1202: "No data record found",
    1300: "Upload failed",
    1301: "Unsupported file format",
    1400: "Parameter format error",
}

UPLOAD_IMAGE_EXTS = {".png", ".jpg", ".gif", ".jpeg", ".webp", ".svg", ".ico"}
UNSET = object()


class APIAbort(Exception):
    def __init__(self, code: int, msg: str, data: Any = UNSET) -> None:
        self.code = code
        self.msg = msg
        self.data = data


@dataclass(slots=True)
class CurrentAccess:
    user: Any
    visit_mode: int = VISIT_MODE_LOGIN


def api_payload(code: int, msg: str, data: Any = UNSET) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "msg": msg}
    if data is not UNSET:
        payload["data"] = data
    return payload


def api_success(data: Any = UNSET) -> JSONResponse:
    return JSONResponse(api_payload(0, "OK", data))


def api_success_list(items: list[Any], count: int) -> JSONResponse:
    return JSONResponse(api_payload(0, "OK", {"list": items, "count": count}))


def error_by_code(code: int) -> APIAbort:
    return APIAbort(code, ERROR_MESSAGES.get(code, "Server error"))


def error_database(_: Exception | str) -> APIAbort:
    return APIAbort(1200, f"Server error[{ERROR_MESSAGES[1200]}]")


def error_param_format(message: str) -> APIAbort:
    if not (message.startswith(" [") and message.endswith("]")):
        message = f" [{message}]"
    return APIAbort(-1, message)


def error_data_not_found() -> APIAbort:
    return APIAbort(-1, "Server error")


async def parse_json_body(request: Request) -> Any:
    try:
        body = await request.body()
        if not body:
            return {}
        return json.loads(body)
    except Exception as exc:
        raise error_param_format(str(exc)) from exc


def validate_required(payload: dict[str, Any], fields: list[tuple[str, str]]) -> None:
    errors = []
    for key, label in fields:
        value = payload.get(key)
        if value is None or value == "":
            errors.append(f" [ {label}为必填字段]")
    if errors:
        raise error_param_format("".join(errors))


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx


def build_client_token(user_id: int) -> str:
    return f"{uuid.uuid4()}-{md5(md5(f'userId{user_id}'))}"


def get_real_token(ctx: AppContext, client_token: str) -> str | None:
    token, ok = ctx.c_user_token.get(client_token)
    return token if ok else None


def fetch_user_by_real_token(ctx: AppContext, real_token: str) -> Any | None:
    with ctx.session() as session:
        user = session.scalar(select(User).where(User.deleted_at.is_(None), User.token == real_token))
        if user is None:
            return None
        return user_to_snapshot(user)


def login_interceptor(request: Request, ctx: AppContext = Depends(get_ctx)) -> CurrentAccess:
    client_token = request.headers.get("token", "")
    if not client_token:
        raise error_by_code(1000)

    real_token = get_real_token(ctx, client_token)
    if not real_token:
        raise error_by_code(1001)

    cached_user, ok = ctx.user_token.get(real_token)
    if ok and cached_user is not None:
        return CurrentAccess(user=cached_user)

    user = fetch_user_by_real_token(ctx, real_token)
    if user is None or not user.token or not user.id:
        raise APIAbort(1001, "")

    ctx.user_token.set_default(user.token, user)
    ctx.c_user_token.set_default(client_token, user.token)
    return CurrentAccess(user=user)


def public_mode_interceptor(request: Request, ctx: AppContext = Depends(get_ctx)) -> CurrentAccess:
    client_token = request.headers.get("token", "")
    if client_token:
        real_token = get_real_token(ctx, client_token)
        if real_token:
            cached_user, ok = ctx.user_token.get(real_token)
            if ok and cached_user is not None:
                return CurrentAccess(user=cached_user)
            user = fetch_user_by_real_token(ctx, real_token)
            if user is not None and user.token:
                ctx.user_token.set_default(user.token, user)
                ctx.c_user_token.set_default(client_token, user.token)
                return CurrentAccess(user=user)

    try:
        public_user_id = ctx.system_setting.get_value_by_interface(PANEL_PUBLIC_USER_ID)
    except Exception:
        raise APIAbort(1001, "")

    if public_user_id is None:
        raise APIAbort(1001, "")

    with ctx.session() as session:
        user = session.scalar(select(User).where(User.deleted_at.is_(None), User.id == int(public_user_id)))
        if user is None:
            raise APIAbort(1001, "")
        return CurrentAccess(user=user_to_snapshot(user), visit_mode=VISIT_MODE_PUBLIC)


def admin_interceptor(access: CurrentAccess = Depends(login_interceptor)) -> CurrentAccess:
    if access.user.role != 1:
        raise APIAbort(1005, "")
    return access


def save_uploaded_file(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)


def add_file_record(ctx: AppContext, user_id: int, file_name: str, ext: str, src: str) -> File:
    with ctx.session() as session:
        row = File(user_id=user_id, file_name=file_name, src=src, ext=ext)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def build_upload_paths(ctx: AppContext, file_name: str, ext: str) -> tuple[Path, str]:
    now = datetime.now(tz=UTC)
    relative_dir = f"{ctx.source_path_raw}/{now.year}/{now.month}/{now.day}"
    relative_path = f"{relative_dir}/{file_name}{ext}"
    absolute_path = ctx.source_path / str(now.year) / str(now.month) / str(now.day) / f"{file_name}{ext}"
    return absolute_path, relative_path


def soft_delete_rows(session: Any, model: Any, *conditions: Any) -> None:
    for row in session.scalars(select(model).where(model.deleted_at.is_(None), *conditions)):
        row.deleted_at = utcnow()


def find_site_icon_url(page_url: str) -> str:
    response = httpx.get(page_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for link in soup.find_all("link"):
        rel = " ".join(link.get("rel", [])) if isinstance(link.get("rel"), list) else str(link.get("rel", ""))
        href = link.get("href")
        if "icon" in rel and href:
            if href.startswith("http://") or href.startswith("https://") or href.startswith("//"):
                return href
            parsed = urlparse(page_url)
            return f"{parsed.scheme}://{parsed.netloc}/{href.lstrip('/')}"
    raise RuntimeError("favicon not found on the page")


def download_image(url: str, save_dir: Path, max_size: int) -> Path:
    head = httpx.head(url, timeout=10, follow_redirects=True)
    head.raise_for_status()
    size = int(head.headers.get("content-length", "0") or 0)
    if size > max_size:
        raise RuntimeError(f"文件太大，不下载。大小：{size}字节")

    response = httpx.get(url, timeout=10, follow_redirects=True)
    response.raise_for_status()
    save_dir.mkdir(parents=True, exist_ok=True)
    file_ext = Path(urlparse(url).path).suffix
    file_name = md5(f"{Path(urlparse(url).path).name}{datetime.now(tz=UTC)}") + file_ext
    target = save_dir / file_name
    target.write_bytes(response.content)
    return target


def cpu_info() -> dict[str, Any]:
    model = ""
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="ignore")
        for line in cpuinfo.splitlines():
            if line.lower().startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    except OSError:
        model = ""
    return {
        "coreCount": 1,
        "cpuNum": psutil.cpu_count(logical=True) or 0,
        "model": model,
        "usages": psutil.cpu_percent(interval=1, percpu=True),
    }


def memory_info() -> dict[str, Any]:
    mem = psutil.virtual_memory()
    return {
        "total": mem.total,
        "free": mem.free,
        "used": mem.used,
        "usedPercent": mem.percent,
    }


def disk_mountpoints() -> list[dict[str, Any]]:
    return [
        {
            "device": part.device,
            "mountpoint": part.mountpoint,
            "fstype": part.fstype,
            "opts": part.opts.split(",") if isinstance(part.opts, str) else part.opts,
        }
        for part in psutil.disk_partitions(all=True)
    ]


def disk_state_by_path(path: str) -> dict[str, Any]:
    usage = psutil.disk_usage(path)
    return {
        "mountpoint": path,
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "usedPercent": usage.percent,
    }


def create_app(ctx: AppContext) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.ctx = ctx

    custom_dir = ctx.web_path / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("index.js", "index.css"):
        file_path = custom_dir / filename
        if not file_path.exists():
            file_path.write_text("", encoding="utf-8")

    @app.exception_handler(APIAbort)
    async def api_abort_handler(_: Request, exc: APIAbort) -> JSONResponse:
        return JSONResponse(api_payload(exc.code, exc.msg, exc.data))

    @app.post("/api/about")
    async def about() -> JSONResponse:
        return api_success({"versionName": ctx.version_info.version, "versionCode": ctx.version_info.version_code})

    @app.post("/api/login")
    async def login(request: Request) -> JSONResponse:
        payload = await parse_json_body(request)
        validate_required(payload, [("username", "Username"), ("password", "Password")])
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        if len(password) > 50:
            raise error_param_format(" [ Password长度不能超过50个字符]")
        with ctx.session() as session:
            user = session.scalar(
                select(User).where(
                    User.deleted_at.is_(None),
                    User.username == username,
                    User.password == password_encryption(password),
                )
            )
            if user is None:
                raise error_by_code(1003)
            if user.status != 1:
                raise error_by_code(1004)
            if not user.token:
                while True:
                    candidate = build_rand_code(32, "abcdefghijklmnopqrstuvwxyz0123456789")
                    duplicate = session.scalar(
                        select(User).where(User.deleted_at.is_(None), User.token == candidate)
                    )
                    if duplicate is None:
                        user.token = candidate
                        session.commit()
                        session.refresh(user)
                        break
            snapshot = user_to_snapshot(user)
        client_token = build_client_token(snapshot.id)
        ctx.c_user_token.set_default(client_token, snapshot.token)
        payload = serialize_user(snapshot, password="", token=client_token)
        payload["referralCode"] = ""
        return api_success(payload)

    @app.post("/api/logout")
    async def logout(request: Request, _: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        client_token = request.headers.get("token", "")
        ctx.c_user_token.delete(client_token)
        return api_success()

    @app.post("/api/user/getInfo")
    async def user_get_info(access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        return api_success(
            {
                "userId": access.user.id,
                "id": access.user.id,
                "headImage": access.user.head_image,
                "name": access.user.name,
                "role": access.user.role,
            }
        )

    @app.post("/api/user/getAuthInfo")
    async def user_get_auth_info(access: CurrentAccess = Depends(public_mode_interceptor)) -> JSONResponse:
        return api_success({"user": serialize_auth_user(access.user), "visitMode": access.visit_mode})

    @app.post("/api/user/updateInfo")
    async def user_update_info(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        name = str(payload.get("name", ""))
        head_image = str(payload.get("headImage", ""))
        if not name or len(name) < 3 or len(name) > 15:
            raise error_param_format("invalid name")
        with ctx.session() as session:
            user = session.scalar(select(User).where(User.deleted_at.is_(None), User.id == access.user.id))
            if user is None:
                raise error_database("not found")
            user.name = name
            user.head_image = head_image
            session.commit()
        ctx.user_token.delete(access.user.token)
        return api_success()

    @app.post("/api/user/updatePassword")
    async def user_update_password(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        old_password = str(payload.get("oldPassword", ""))
        new_password = str(payload.get("newPassword", ""))
        with ctx.session() as session:
            user = session.scalar(select(User).where(User.deleted_at.is_(None), User.id == access.user.id))
            if user is None:
                raise error_param_format("record not found")
            if user.password != password_encryption(old_password):
                raise error_by_code(1007)
            user.password = password_encryption(new_password)
            user.token = ""
            session.commit()
        ctx.user_token.delete(access.user.token)
        return api_success()

    @app.post("/api/user/getReferralCode")
    async def user_get_referral_code(access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        with ctx.session() as session:
            user = session.scalar(select(User).where(User.deleted_at.is_(None), User.id == access.user.id))
            if user is None:
                raise error_database("not found")
            if not user.referral_code:
                while True:
                    code = build_rand_code(8, "abcdefghijklmnopqrstuvwxyz0123456789")
                    duplicate = session.scalar(
                        select(User).where(User.deleted_at.is_(None), User.referral_code == code)
                    )
                    if duplicate is None:
                        user.referral_code = code
                        session.commit()
                        session.refresh(user)
                        break
            return api_success({"referralCode": user.referral_code})

    @app.post("/api/file/uploadImg")
    async def file_upload_img(
        access: CurrentAccess = Depends(login_interceptor),
        imgfile: UploadFile = FastAPIFile(...),
    ) -> JSONResponse:
        ext = Path(imgfile.filename or "").suffix.lower()
        if ext not in UPLOAD_IMAGE_EXTS:
            raise error_by_code(1301)
        file_name = md5(f"{imgfile.filename}{datetime.now(tz=UTC)}")
        absolute_path, relative_path = build_upload_paths(ctx, file_name, ext)
        save_uploaded_file(imgfile, absolute_path)
        add_file_record(ctx, access.user.id, imgfile.filename or "", ext, relative_path)
        return api_success({"imageUrl": relative_path[1:]})

    @app.post("/api/file/uploadFiles")
    async def file_upload_files(
        access: CurrentAccess = Depends(login_interceptor),
        files: list[UploadFile] = FastAPIFile(..., alias="files[]"),
    ) -> JSONResponse:
        err_files: list[str] = []
        succ_map: dict[str, str] = {}
        for upload in files:
            ext = Path(upload.filename or "").suffix.lower()
            file_name = md5(f"{upload.filename}{datetime.now(tz=UTC)}")
            absolute_path, relative_path = build_upload_paths(ctx, file_name, ext)
            try:
                save_uploaded_file(upload, absolute_path)
            except Exception:
                err_files.append(upload.filename or "")
                continue
            add_file_record(ctx, access.user.id, upload.filename or "", ext, relative_path)
            succ_map[upload.filename or ""] = relative_path[1:]
        return api_success({"succMap": succ_map, "errFiles": err_files})

    @app.post("/api/file/getList")
    async def file_get_list(access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        with ctx.session() as session:
            files = list(
                session.scalars(
                    select(File)
                    .where(File.deleted_at.is_(None), File.user_id == access.user.id)
                    .order_by(File.created_at.desc())
                )
            )
        data = [
            {
                "src": file.src[1:],
                "fileName": file.file_name,
                "id": file.id,
                "createTime": format_time(file.created_at),
                "updateTime": format_time(file.updated_at),
                "path": file.src,
            }
            for file in files
        ]
        return api_success({"list": data, "count": len(data)})

    @app.post("/api/file/deletes")
    async def file_deletes(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        ids = payload.get("ids", [])
        with ctx.session() as session:
            files = list(
                session.scalars(
                    select(File).where(File.deleted_at.is_(None), File.user_id == access.user.id, File.id.in_(ids))
                )
            )
            for file in files:
                try:
                    target = Path(file.src)
                    os.remove(target if target.is_absolute() else (ctx.runtime_root / file.src).resolve())
                except FileNotFoundError:
                    pass
                file.deleted_at = utcnow()
            session.commit()
        return api_success()

    @app.post("/api/notice/getListByDisplayType")
    async def notice_get_list_by_display_type(request: Request) -> JSONResponse:
        payload = await parse_json_body(request)
        display_types = payload.get("displayType", [])
        try:
            with ctx.session() as session:
                placeholders = ",".join(str(int(item)) for item in display_types) or "0"
                rows = session.execute(text(f"SELECT * FROM notice WHERE display_type IN ({placeholders})")).mappings().all()
        except Exception as exc:
            raise error_database(exc) from exc
        data = [
            {
                "ID": 0,
                "CreatedAt": ZERO_TIME,
                "UpdatedAt": ZERO_TIME,
                "DeletedAt": None,
                "id": row.get("id", 0) or 0,
                "createTime": ZERO_TIME if row.get("created_at") is None else format_time(row.get("created_at")),
                "updateTime": ZERO_TIME if row.get("updated_at") is None else format_time(row.get("updated_at")),
                "title": row.get("title", "") or "",
                "content": row.get("content", "") or "",
                "displayType": row.get("display_type", 0) or 0,
                "oneRead": row.get("one_read", 0) or 0,
                "url": row.get("url", "") or "",
                "isLogin": row.get("is_login", 0) or 0,
                "userId": row.get("user_id", 0) or 0,
                "user": serialize_zero_user(),
            }
            for row in rows
        ]
        return api_success({"list": data, "count": 0})

    @app.post("/api/system/moduleConfig/getByName")
    async def module_config_get_by_name(request: Request, access: CurrentAccess = Depends(public_mode_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        name = str(payload.get("name", ""))
        with ctx.session() as session:
            config = session.scalar(
                select(ModuleConfig).where(
                    ModuleConfig.deleted_at.is_(None),
                    ModuleConfig.user_id == access.user.id,
                    ModuleConfig.name == name,
                )
            )
            if config is None:
                return api_success(None)
            try:
                value = json.loads(config.value_json)
            except json.JSONDecodeError:
                value = None
            return api_success(value)

    @app.post("/api/system/moduleConfig/save")
    async def module_config_save(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        name = str(payload.get("name", ""))
        value = payload.get("value")
        value_json = json.dumps(value, ensure_ascii=False) if value is not None else "null"
        with ctx.session() as session:
            config = session.scalar(
                select(ModuleConfig).where(
                    ModuleConfig.deleted_at.is_(None),
                    ModuleConfig.user_id == access.user.id,
                    ModuleConfig.name == name,
                )
            )
            if config is None:
                session.add(ModuleConfig(user_id=access.user.id, name=name, value_json=value_json))
            else:
                config.name = name
                config.user_id = access.user.id
                config.value_json = value_json
            session.commit()
        return api_success()

    @app.post("/api/system/monitor/getAll")
    async def monitor_get_all(access: CurrentAccess = Depends(public_mode_interceptor)) -> JSONResponse:
        value, ok = ctx.system_monitor.get("value")
        if ok:
            return api_success(value)
        raise APIAbort(-1, "failed")

    @app.post("/api/system/monitor/getCpuState")
    async def monitor_get_cpu_state(access: CurrentAccess = Depends(public_mode_interceptor)) -> JSONResponse:
        value, ok = ctx.system_monitor.get(SYSTEM_MONITOR_CPU_INFO)
        if ok:
            return api_success(value)
        info = cpu_info()
        ctx.system_monitor.set(SYSTEM_MONITOR_CPU_INFO, info, timedelta(seconds=3))
        return api_success(info)

    @app.post("/api/system/monitor/getMemonyState")
    async def monitor_get_memory_state(access: CurrentAccess = Depends(public_mode_interceptor)) -> JSONResponse:
        value, ok = ctx.system_monitor.get(SYSTEM_MONITOR_MEMORY_INFO)
        if ok:
            return api_success(value)
        info = memory_info()
        ctx.system_monitor.set(SYSTEM_MONITOR_MEMORY_INFO, info, timedelta(seconds=3))
        return api_success(info)

    @app.post("/api/system/monitor/getDiskStateByPath")
    async def monitor_get_disk_state_by_path(request: Request, access: CurrentAccess = Depends(public_mode_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        path = str(payload.get("path", ""))
        cache_key = SYSTEM_MONITOR_DISK_INFO + path
        value, ok = ctx.system_monitor.get(cache_key)
        if ok:
            return api_success(value)
        try:
            info = disk_state_by_path(path)
        except Exception as exc:
            raise APIAbort(-1, "failed") from exc
        ctx.system_monitor.set(cache_key, info, timedelta(seconds=3))
        return api_success(info)

    @app.post("/api/system/monitor/getDiskMountpoints")
    async def monitor_get_disk_mountpoints(_: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        return api_success(disk_mountpoints())

    @app.post("/api/panel/itemIcon/edit")
    async def item_icon_edit(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        if not payload.get("itemIconGroupId"):
            raise error_param_format("Group is mandatory")
        icon_json = json.dumps(payload.get("icon"), ensure_ascii=False) if "icon" in payload else ""
        with ctx.session() as session:
            if payload.get("id"):
                icon = session.scalar(select(ItemIcon).where(ItemIcon.deleted_at.is_(None), ItemIcon.id == int(payload["id"])))
                if icon is None:
                    raise error_data_not_found()
                icon.icon_json = icon_json
                icon.title = str(payload.get("title", ""))
                icon.url = str(payload.get("url", ""))
                icon.lan_url = str(payload.get("lanUrl", ""))
                icon.description = str(payload.get("description", ""))
                icon.open_method = int(payload.get("openMethod", 0) or 0)
                icon.user_id = access.user.id
                icon.item_icon_group_id = int(payload.get("itemIconGroupId", 0) or 0)
                if payload.get("sort"):
                    icon.sort = int(payload.get("sort", 0))
                session.commit()
                response_payload = serialize_item_icon(icon)
                response_payload.update(
                    {
                        "createTime": ZERO_TIME,
                        "updateTime": ZERO_TIME,
                        "icon": payload.get("icon"),
                        "title": str(payload.get("title", "")),
                        "url": str(payload.get("url", "")),
                        "lanUrl": str(payload.get("lanUrl", "")),
                        "description": str(payload.get("description", "")),
                        "openMethod": int(payload.get("openMethod", 0) or 0),
                        "sort": int(payload.get("sort", 0) or 0),
                        "itemIconGroupId": int(payload.get("itemIconGroupId", 0) or 0),
                        "userId": access.user.id,
                    }
                )
                return api_success(response_payload)
            else:
                icon = ItemIcon(
                    icon_json=icon_json,
                    title=str(payload.get("title", "")),
                    url=str(payload.get("url", "")),
                    lan_url=str(payload.get("lanUrl", "")),
                    description=str(payload.get("description", "")),
                    open_method=int(payload.get("openMethod", 0) or 0),
                    sort=9999,
                    item_icon_group_id=int(payload.get("itemIconGroupId", 0) or 0),
                    user_id=access.user.id,
                )
                session.add(icon)
            session.commit()
            session.refresh(icon)
            return api_success(serialize_item_icon(icon))

    @app.post("/api/panel/itemIcon/addMultiple")
    async def item_icon_add_multiple(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        if not isinstance(payload, list):
            raise error_param_format("json: cannot unmarshal object into Go value of type []models.ItemIcon")
        rows = []
        with ctx.session() as session:
            for item in payload:
                if not item.get("itemIconGroupId"):
                    raise error_param_format("Group is mandatory")
                row = ItemIcon(
                    icon_json=json.dumps(item.get("icon"), ensure_ascii=False),
                    title=str(item.get("title", "")),
                    url=str(item.get("url", "")),
                    lan_url=str(item.get("lanUrl", "")),
                    description=str(item.get("description", "")),
                    open_method=int(item.get("openMethod", 0) or 0),
                    sort=int(item.get("sort", 0) or 0),
                    item_icon_group_id=int(item.get("itemIconGroupId", 0) or 0),
                    user_id=access.user.id,
                )
                session.add(row)
                rows.append(row)
            session.commit()
            for row in rows:
                session.refresh(row)
        return api_success([serialize_item_icon(row) for row in rows])

    @app.post("/api/panel/itemIcon/getListByGroupId")
    async def item_icon_get_list_by_group_id(request: Request, access: CurrentAccess = Depends(public_mode_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        group_id = int(payload.get("itemIconGroupId", 0) or 0)
        with ctx.session() as session:
            rows = list(
                session.scalars(
                    select(ItemIcon)
                    .where(
                        ItemIcon.deleted_at.is_(None),
                        ItemIcon.item_icon_group_id == group_id,
                        ItemIcon.user_id == access.user.id,
                    )
                    .order_by(ItemIcon.sort.asc(), ItemIcon.created_at.asc())
                )
            )
        return api_success({"list": [serialize_item_icon(row) for row in rows], "count": 0})

    @app.post("/api/panel/itemIcon/deletes")
    async def item_icon_deletes(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        ids = payload.get("ids", [])
        with ctx.session() as session:
            rows = list(
                session.scalars(
                    select(ItemIcon).where(
                        ItemIcon.deleted_at.is_(None),
                        ItemIcon.user_id == access.user.id,
                        ItemIcon.id.in_(ids),
                    )
                )
            )
            for row in rows:
                row.deleted_at = utcnow()
            session.commit()
        return api_success()

    @app.post("/api/panel/itemIcon/saveSort")
    async def item_icon_save_sort(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        group_id = int(payload.get("itemIconGroupId", 0) or 0)
        with ctx.session() as session:
            for item in payload.get("sortItems", []):
                row = session.scalar(
                    select(ItemIcon).where(
                        ItemIcon.deleted_at.is_(None),
                        ItemIcon.user_id == access.user.id,
                        ItemIcon.id == int(item.get("id", 0) or 0),
                        ItemIcon.item_icon_group_id == group_id,
                    )
                )
                if row is not None:
                    row.sort = int(item.get("sort", 0) or 0)
            session.commit()
        return api_success()

    @app.post("/api/panel/itemIcon/getSiteFavicon")
    async def item_icon_get_site_favicon(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        raw_url = str(payload.get("url", ""))
        try:
            full_url = find_site_icon_url(raw_url)
        except Exception as exc:
            raise error_param_format(f"acquisition failed: get ico error:{exc}") from exc
        parsed_url = urlparse(raw_url)
        if full_url.startswith("//"):
            full_url = f"{parsed_url.scheme}://{full_url[2:]}"
        elif not full_url.startswith(("http://", "https://")):
            full_url = f"http://{full_url}"
        parsed_icon = urlparse(full_url)
        full_url = f"{parsed_icon.scheme}://{parsed_icon.netloc}{parsed_icon.path}"
        ext = Path(urlparse(full_url).path).suffix
        file_name = md5(f"{Path(urlparse(full_url).path).name}{datetime.now(tz=UTC)}")
        absolute_path, relative_path = build_upload_paths(ctx, file_name, ext)
        relative_path = relative_path.replace(f"/{file_name}{ext}", f"//{file_name}{ext}")
        save_dir = absolute_path.parent
        try:
            image = download_image(full_url, save_dir, 1024 * 1024)
        except Exception as exc:
            raise error_param_format(f"acquisition failed: download{exc}") from exc
        if image != absolute_path:
            absolute_path.write_bytes(image.read_bytes())
            image.unlink(missing_ok=True)
        add_file_record(ctx, access.user.id, parsed_url.netloc, ext, relative_path)
        return api_success({"iconUrl": relative_path[1:]})

    @app.post("/api/panel/userConfig/get")
    async def user_config_get(access: CurrentAccess = Depends(public_mode_interceptor)) -> JSONResponse:
        with ctx.session() as session:
            cfg = session.scalar(select(UserConfig).where(UserConfig.user_id == access.user.id))
            if cfg is None:
                raise error_data_not_found()
            return api_success(serialize_user_config(cfg))

    @app.post("/api/panel/userConfig/set")
    async def user_config_set(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        panel_json = json.dumps(payload.get("panel"), ensure_ascii=False) if "panel" in payload else "null"
        search_engine_json = json.dumps(payload.get("searchEngine"), ensure_ascii=False) if "searchEngine" in payload else "null"
        with ctx.session() as session:
            cfg = session.scalar(select(UserConfig).where(UserConfig.user_id == access.user.id))
            if cfg is None:
                session.add(UserConfig(user_id=access.user.id, panel_json=panel_json, search_engine_json=search_engine_json))
            else:
                cfg.panel_json = panel_json
                cfg.search_engine_json = search_engine_json
            session.commit()
        return api_success()

    @app.post("/api/panel/itemIconGroup/edit")
    async def item_icon_group_edit(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        with ctx.session() as session:
            if payload.get("id"):
                group = session.scalar(
                    select(ItemIconGroup).where(ItemIconGroup.deleted_at.is_(None), ItemIconGroup.id == int(payload["id"]))
                )
                if group is None:
                    raise error_data_not_found()
                group.icon = str(payload.get("icon", ""))
                group.title = str(payload.get("title", ""))
                group.description = str(payload.get("description", ""))
                group.user_id = access.user.id
                if payload.get("sort"):
                    group.sort = int(payload.get("sort", 0) or 0)
                session.commit()
                response_payload = serialize_item_icon_group(group)
                response_payload.update(
                    {
                        "createTime": ZERO_TIME,
                        "updateTime": ZERO_TIME,
                        "icon": str(payload.get("icon", "")),
                        "title": str(payload.get("title", "")),
                        "description": str(payload.get("description", "")),
                        "sort": int(payload.get("sort", 0) or 0),
                        "userId": access.user.id,
                    }
                )
                return api_success(response_payload)
            else:
                group = ItemIconGroup(
                    icon=str(payload.get("icon", "")),
                    title=str(payload.get("title", "")),
                    description=str(payload.get("description", "")),
                    sort=int(payload.get("sort", 0) or 0),
                    user_id=access.user.id,
                )
                session.add(group)
            session.commit()
            session.refresh(group)
            return api_success(serialize_item_icon_group(group))

    @app.post("/api/panel/itemIconGroup/getList")
    async def item_icon_group_get_list(access: CurrentAccess = Depends(public_mode_interceptor)) -> JSONResponse:
        with ctx.session() as session:
            groups = list(
                session.scalars(
                    select(ItemIconGroup)
                    .where(ItemIconGroup.deleted_at.is_(None), ItemIconGroup.user_id == access.user.id)
                    .order_by(ItemIconGroup.sort.asc(), ItemIconGroup.created_at.asc())
                )
            )
            if not groups:
                group = ItemIconGroup(title="APP", user_id=access.user.id, icon="material-symbols:ad-group-outline")
                session.add(group)
                session.commit()
                session.refresh(group)
                for icon in session.scalars(
                    select(ItemIcon).where(ItemIcon.deleted_at.is_(None), ItemIcon.user_id == access.user.id)
                ):
                    icon.item_icon_group_id = group.id
                session.commit()
                groups = [group]
        return api_success({"list": [serialize_item_icon_group(group) for group in groups], "count": 0})

    @app.post("/api/panel/itemIconGroup/deletes")
    async def item_icon_group_deletes(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        ids = payload.get("ids", [])
        with ctx.session() as session:
            count = session.scalar(
                select(func.count()).select_from(ItemIconGroup).where(
                    ItemIconGroup.deleted_at.is_(None), ItemIconGroup.user_id == access.user.id
                )
            ) or 0
            if abs(len(ids) - count) < 1:
                raise APIAbort(1201, "At least one must be retained")
            groups = list(
                session.scalars(
                    select(ItemIconGroup).where(
                        ItemIconGroup.deleted_at.is_(None),
                        ItemIconGroup.user_id == access.user.id,
                        ItemIconGroup.id.in_(ids),
                    )
                )
            )
            for group in groups:
                group.deleted_at = utcnow()
            icons = list(
                session.scalars(
                    select(ItemIcon).where(
                        ItemIcon.deleted_at.is_(None),
                        ItemIcon.user_id == access.user.id,
                        ItemIcon.item_icon_group_id.in_(ids),
                    )
                )
            )
            for icon in icons:
                icon.deleted_at = utcnow()
            session.commit()
        return api_success()

    @app.post("/api/panel/itemIconGroup/saveSort")
    async def item_icon_group_save_sort(request: Request, access: CurrentAccess = Depends(login_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        with ctx.session() as session:
            for item in payload.get("sortItems", []):
                group = session.scalar(
                    select(ItemIconGroup).where(
                        ItemIconGroup.deleted_at.is_(None),
                        ItemIconGroup.user_id == access.user.id,
                        ItemIconGroup.id == int(item.get("id", 0) or 0),
                    )
                )
                if group is not None:
                    group.sort = int(item.get("sort", 0) or 0)
            session.commit()
        return api_success()

    @app.post("/api/panel/users/create")
    async def users_create(request: Request, _: CurrentAccess = Depends(admin_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        validate_required(payload, [("username", "Username"), ("password", "Password")])
        username = str(payload.get("username", "")).strip()
        if len(username) < 5:
            raise error_param_format("The account must be no less than 5 characters long")
        with ctx.session() as session:
            duplicate = session.scalar(select(User).where(User.deleted_at.is_(None), User.username == username))
            if duplicate is not None:
                raise error_by_code(1006)
            user = User(
                username=username,
                password=password_encryption(str(payload.get("password", ""))),
                name=str(payload.get("name", "")),
                head_image=str(payload.get("headImage", "")),
                status=1,
                role=int(payload.get("role", 0) or 0),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return api_success({"userId": user.id})

    @app.post("/api/panel/users/update")
    async def users_update(request: Request, _: CurrentAccess = Depends(admin_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        if payload.get("password", "") == "":
            payload["password"] = "-"
        validate_required(payload, [("username", "Username"), ("password", "Password")])
        username = str(payload.get("username", "")).strip()
        if len(username) < 3:
            raise error_param_format("The account must be no less than 3 characters long")
        with ctx.session() as session:
            duplicate = session.scalar(select(User).where(User.deleted_at.is_(None), User.username == username))
            user_info = duplicate
            old_token = user_info.token if user_info is not None else ""
            if duplicate is not None and duplicate.id != int(payload.get("id", 0) or 0):
                raise error_by_code(1006)
            user = session.scalar(select(User).where(User.deleted_at.is_(None), User.id == int(payload.get("id", 0) or 0)))
            if user is None:
                raise error_data_not_found()
            user.username = username
            user.name = str(payload.get("name", ""))
            user.mail = str(payload.get("mail", ""))
            user.token = ""
            user.role = int(payload.get("role", 0) or 0)
            if payload.get("password") != "-":
                user.password = password_encryption(str(payload.get("password", "")))
            session.commit()
            session.refresh(user)
            ctx.user_token.delete(old_token)
        response_payload = serialize_zero_user()
        response_payload.update(
            {
                "id": int(payload.get("id", 0) or 0),
                "createTime": "0001-01-01T00:00:00Z",
                "updateTime": format_time(user.updated_at),
                "username": username,
                "password": payload.get("password") if payload.get("password") == "-" else password_encryption(str(payload.get("password", ""))),
                "name": str(payload.get("name", "")),
                "mail": str(payload.get("mail", "")),
                "role": int(payload.get("role", 0) or 0),
                "token": "",
            }
        )
        return api_success(response_payload)

    @app.post("/api/panel/users/getList")
    async def users_get_list(request: Request, _: CurrentAccess = Depends(admin_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        page = int(payload.get("page", 1) or 1)
        limit = int(payload.get("limit", 10) or 10)
        keyword = str(payload.get("keyword", ""))
        with ctx.session() as session:
            query = select(User).where(User.deleted_at.is_(None))
            count_query = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
            if keyword:
                like = f"%{keyword}%"
                query = query.where((User.name.like(like)) | (User.username.like(like)))
                count_query = count_query.where((User.name.like(like)) | (User.username.like(like)))
            users = list(session.scalars(query.offset((page - 1) * limit).limit(limit)))
            count = session.scalar(count_query) or 0
        result = []
        for user in users:
            snapshot = user_to_snapshot(user)
            snapshot.password = ""
            result.append(serialize_user(snapshot))
        return api_success({"list": result, "count": count})

    @app.post("/api/panel/users/deletes")
    async def users_deletes(request: Request, _: CurrentAccess = Depends(admin_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        user_ids = payload.get("userIds", [])
        with ctx.session() as session:
            for user_id in user_ids:
                for row in session.scalars(select(ItemIcon).where(ItemIcon.deleted_at.is_(None), ItemIcon.user_id == int(user_id))):
                    row.deleted_at = utcnow()
                for row in session.scalars(
                    select(ItemIconGroup).where(ItemIconGroup.deleted_at.is_(None), ItemIconGroup.user_id == int(user_id))
                ):
                    row.deleted_at = utcnow()
                for row in session.scalars(
                    select(ModuleConfig).where(ModuleConfig.deleted_at.is_(None), ModuleConfig.user_id == int(user_id))
                ):
                    row.deleted_at = utcnow()
                for row in session.scalars(
                    select(ModuleConfig).where(ModuleConfig.deleted_at.is_(None), ModuleConfig.user_id == int(user_id))
                ):
                    row.deleted_at = utcnow()
            for user in session.scalars(select(User).where(User.deleted_at.is_(None), User.id.in_(user_ids))):
                user.deleted_at = utcnow()
            admin_count = session.scalar(select(func.count()).select_from(User).where(User.deleted_at.is_(None), User.role == 1)) or 0
            if admin_count == 0:
                session.rollback()
                raise error_by_code(1201)
            session.commit()
        return api_success()

    @app.post("/api/panel/users/setPublicVisitUser")
    async def users_set_public_visit_user(request: Request, _: CurrentAccess = Depends(admin_interceptor)) -> JSONResponse:
        payload = await parse_json_body(request)
        user_id = payload.get("userId")
        if user_id is not None:
            with ctx.session() as session:
                user = session.scalar(select(User).where(User.deleted_at.is_(None), User.id == int(user_id)))
                if user is None:
                    raise error_data_not_found()
        try:
            ctx.system_setting.set(PANEL_PUBLIC_USER_ID, user_id)
        except Exception:
            raise error_param_format("set fail")
        return api_success()

    @app.post("/api/panel/users/getPublicVisitUser")
    async def users_get_public_visit_user(_: CurrentAccess = Depends(admin_interceptor)) -> JSONResponse:
        try:
            user_id = ctx.system_setting.get_value_by_interface(PANEL_PUBLIC_USER_ID)
        except Exception:
            raise error_data_not_found()
        if user_id is None:
            raise error_data_not_found()
        with ctx.session() as session:
            user = session.scalar(select(User).where(User.deleted_at.is_(None), User.id == int(user_id)))
            if user is None:
                raise error_data_not_found()
            return api_success(serialize_user(user_to_snapshot(user)))

    @app.get("/api/openness/loginConfig")
    async def openness_login_config() -> JSONResponse:
        try:
            cfg = ctx.system_setting.get_value_by_interface("system_application")
        except MissingSettingError as exc:
            raise APIAbort(-1, f"配置查询失败：{exc}") from exc
        return api_success(
            {
                "loginCaptcha": bool(cfg.get("loginCaptcha")),
                "register": {
                    "emailSuffix": cfg.get("emailSuffix", ""),
                    "openRegister": bool(cfg.get("openRegister")),
                },
            }
        )

    @app.get("/api/openness/getDisclaimer")
    async def openness_get_disclaimer() -> JSONResponse:
        try:
            content = ctx.system_setting.get_value_string(DISCLAIMER)
        except Exception:
            ctx.system_setting.set(DISCLAIMER, "")
            return api_success("")
        return api_success(content)

    @app.get("/api/openness/getAboutDescription")
    async def openness_get_about_description() -> JSONResponse:
        try:
            content = ctx.system_setting.get_value_string(WEB_ABOUT_DESCRIPTION)
        except Exception:
            ctx.system_setting.set(WEB_ABOUT_DESCRIPTION, "")
            return api_success("")
        return api_success(content)

    @app.get("/")
    async def web_index() -> FileResponse:
        target = ctx.web_path / "index.html"
        if not target.exists():
            raise APIAbort(-1, "Not Found")
        return FileResponse(target)

    @app.get("/favicon.ico")
    async def web_favicon_ico() -> FileResponse:
        target = ctx.web_path / "favicon.ico"
        if not target.exists():
            raise APIAbort(-1, "Not Found")
        return FileResponse(target)

    @app.get("/favicon.svg")
    async def web_favicon_svg() -> FileResponse:
        target = ctx.web_path / "favicon.svg"
        if not target.exists():
            raise APIAbort(-1, "Not Found")
        return FileResponse(target)

    app.mount("/assets", StaticFiles(directory=ctx.web_path / "assets", check_dir=False), name="assets")
    app.mount("/custom", StaticFiles(directory=ctx.web_path / "custom", check_dir=False), name="custom")

    source_path_raw = ctx.config.get_value_string("base", "source_path") or "./uploads"
    static_route = source_path_raw[1:] if source_path_raw else source_path_raw
    app.mount(static_route, StaticFiles(directory=ctx.source_path, check_dir=False), name="uploads")
    return app


def run(ctx: AppContext) -> None:
    app = create_app(ctx)
    ctx.logger.info("Sun-Panel is Started.  Listening and serving HTTP on :%s", ctx.http_port)
    uvicorn.run(app, host="0.0.0.0", port=ctx.http_port, log_level="info")
