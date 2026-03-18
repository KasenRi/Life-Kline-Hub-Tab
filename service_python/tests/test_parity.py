from __future__ import annotations

import base64
import contextlib
import http.server
import json
import os
import re
import shutil
import socket
import socketserver
import sqlite3
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Iterator

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_BIN = REPO_ROOT / "service_python" / ".venv" / "bin" / "python"
PYTHONPATH = str(REPO_ROOT / "service_python")
CONF_EXAMPLE = REPO_ROOT / "service_python" / "assets" / "conf.example.ini"
GO_BUILD_DIR = Path(tempfile.gettempdir()) / "sun-panel-go-test-build"
GO_PARITY_ENABLED = os.getenv("SUN_PANEL_ENABLE_GO_PARITY") == "1"

ZERO_TIME = "0001-01-01T00:00:00Z"
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2pH6kAAAAASUVORK5CYII="
)
SVG_ICON = b"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'><rect width='1' height='1' fill='red'/></svg>"

ALL_API_ROUTES = {
    "/about",
    "/login",
    "/logout",
    "/user/getInfo",
    "/user/updatePassword",
    "/user/updateInfo",
    "/user/getReferralCode",
    "/user/getAuthInfo",
    "/file/uploadImg",
    "/file/uploadFiles",
    "/file/getList",
    "/file/deletes",
    "/notice/getListByDisplayType",
    "/system/moduleConfig/save",
    "/system/moduleConfig/getByName",
    "/system/monitor/getDiskMountpoints",
    "/system/monitor/getAll",
    "/system/monitor/getCpuState",
    "/system/monitor/getDiskStateByPath",
    "/system/monitor/getMemonyState",
    "/panel/itemIcon/edit",
    "/panel/itemIcon/deletes",
    "/panel/itemIcon/saveSort",
    "/panel/itemIcon/addMultiple",
    "/panel/itemIcon/getSiteFavicon",
    "/panel/itemIcon/getListByGroupId",
    "/panel/userConfig/set",
    "/panel/userConfig/get",
    "/panel/users/create",
    "/panel/users/update",
    "/panel/users/getList",
    "/panel/users/deletes",
    "/panel/users/getPublicVisitUser",
    "/panel/users/setPublicVisitUser",
    "/panel/itemIconGroup/edit",
    "/panel/itemIconGroup/deletes",
    "/panel/itemIconGroup/saveSort",
    "/panel/itemIconGroup/getList",
    "/openness/loginConfig",
    "/openness/getDisclaimer",
    "/openness/getAboutDescription",
}

STATIC_ROUTES = {
    "/",
    "/assets/hello.txt",
    "/custom/theme.css",
    "/favicon.ico",
    "/favicon.svg",
}


def make_conf(runtime_root: Path, port: int) -> None:
    conf_dir = runtime_root / "conf"
    conf_dir.mkdir(parents=True, exist_ok=True)
    text = CONF_EXAMPLE.read_text(encoding="utf-8")
    text = text.replace("http_port=3002", f"http_port={port}")
    (conf_dir / "conf.ini").write_text(text, encoding="utf-8")
    (conf_dir / "conf.example.ini").write_text(text, encoding="utf-8")


def make_web(runtime_root: Path) -> None:
    web_root = runtime_root / "web"
    (web_root / "assets").mkdir(parents=True, exist_ok=True)
    (web_root / "custom").mkdir(parents=True, exist_ok=True)
    (web_root / "index.html").write_text("<!doctype html><html><body>sun-panel test</body></html>", encoding="utf-8")
    (web_root / "assets" / "hello.txt").write_text("asset-ok\n", encoding="utf-8")
    (web_root / "custom" / "theme.css").write_text("body{background:#fff;}\n", encoding="utf-8")
    (web_root / "favicon.ico").write_bytes(PNG_1X1)
    (web_root / "favicon.svg").write_bytes(SVG_ICON)


def wait_for_port(port: int, timeout: float = 20) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise TimeoutError(f"port {port} did not open in time")


def stop_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def wait_for_path(path: Path, timeout: float = 10) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists():
            return
        time.sleep(0.1)
    raise TimeoutError(f"path {path} did not appear in time")


def ensure_go_binary() -> Path:
    output = GO_BUILD_DIR / "sun-panel"
    if output.exists():
        return output
    GO_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["go", "build", "-o", str(output), "main.go"],
        cwd=REPO_ROOT / "service",
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return output


@contextlib.contextmanager
def running_go_service(port: int) -> Iterator["ServiceClient"]:
    go_binary = ensure_go_binary()
    with tempfile.TemporaryDirectory(prefix="sun-panel-go-") as tmp:
        runtime_root = Path(tmp)
        shutil.copy2(go_binary, runtime_root / "sun-panel")
        make_conf(runtime_root, port)
        make_web(runtime_root)
        proc = subprocess.Popen(
            [str(runtime_root / "sun-panel")],
            cwd=runtime_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            wait_for_port(port)
            yield ServiceClient("go", f"http://127.0.0.1:{port}", runtime_root)
        finally:
            stop_process(proc)


@contextlib.contextmanager
def running_python_service(port: int) -> Iterator["ServiceClient"]:
    if not PYTHON_BIN.exists():
        raise AssertionError(f"missing Python venv interpreter at {PYTHON_BIN}")
    with tempfile.TemporaryDirectory(prefix="sun-panel-python-") as tmp:
        runtime_root = Path(tmp)
        make_conf(runtime_root, port)
        make_web(runtime_root)
        env = os.environ.copy()
        env["PYTHONPATH"] = PYTHONPATH
        proc = subprocess.Popen(
            [str(PYTHON_BIN), "-m", "sun_panel_python"],
            cwd=runtime_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        try:
            wait_for_port(port)
            yield ServiceClient("python", f"http://127.0.0.1:{port}", runtime_root)
        finally:
            stop_process(proc)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        _ = format, args


@contextlib.contextmanager
def local_site() -> Iterator[str]:
    with tempfile.TemporaryDirectory(prefix="sun-panel-favicon-") as tmp:
        root = Path(tmp)
        (root / "index.html").write_text(
            "<html><head><link rel='icon' href='/favicon.ico?cache=1'></head><body>ok</body></html>",
            encoding="utf-8",
        )
        (root / "favicon.ico").write_bytes(PNG_1X1)

        class Handler(QuietHandler):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, directory=str(root), **kwargs)

        with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield f"http://127.0.0.1:{server.server_address[1]}/index.html"
            finally:
                server.shutdown()
                thread.join(timeout=5)


class ServiceClient:
    def __init__(self, name: str, root_url: str, runtime_root: Path) -> None:
        self.name = name
        self.runtime_root = runtime_root
        self.root_client = httpx.Client(base_url=root_url, timeout=30.0)
        self.client = httpx.Client(base_url=f"{root_url}/api", timeout=30.0)
        self.api_hits: set[str] = set()
        self.static_hits: set[str] = set()

    def close(self) -> None:
        self.root_client.close()
        self.client.close()

    def get(self, path: str, *, token: str | None = None) -> dict[str, Any]:
        self.api_hits.add(path)
        headers = {"token": token} if token else {}
        return self.client.get(path, headers=headers).json()

    def post(self, path: str, data: Any | None = None, *, token: str | None = None) -> dict[str, Any]:
        self.api_hits.add(path)
        headers = {"token": token} if token else {}
        return self.client.post(path, headers=headers, json=data or {}).json()

    def upload(
        self,
        path: str,
        field: str,
        filename: str,
        content: bytes,
        content_type: str,
        *,
        token: str | None = None,
    ) -> dict[str, Any]:
        self.api_hits.add(path)
        headers = {"token": token} if token else {}
        return self.client.post(
            path,
            headers=headers,
            files={field: (filename, content, content_type)},
        ).json()

    def upload_many(
        self,
        path: str,
        files: list[tuple[str, str, bytes, str]],
        *,
        token: str | None = None,
    ) -> dict[str, Any]:
        self.api_hits.add(path)
        headers = {"token": token} if token else {}
        return self.client.post(
            path,
            headers=headers,
            files=[(field, (filename, content, content_type)) for field, filename, content, content_type in files],
        ).json()

    def root_get(self, path: str, *, token: str | None = None) -> httpx.Response:
        self.static_hits.add(path)
        headers = {"token": token} if token else {}
        return self.root_client.get(path, headers=headers)


def seed_success_data(service: ServiceClient) -> None:
    db_path = service.runtime_root / "database" / "database.db"
    wait_for_path(db_path)
    application_setting = {
        "emailSuffix": "@example.com",
        "openRegister": True,
        "loginCaptcha": True,
        "webSiteUrl": "http://example.com",
    }
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notice (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at DATETIME,
                updated_at DATETIME,
                deleted_at DATETIME,
                title VARCHAR(255),
                content VARCHAR(2000),
                display_type INTEGER,
                one_read INTEGER,
                url VARCHAR(255),
                is_login INTEGER,
                user_id INTEGER
            )
            """
        )
        conn.execute("DELETE FROM notice")
        conn.executemany(
            "INSERT INTO notice (title, content, display_type, one_read, url, is_login, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("Login notice", "Shown on login", 1, 0, "http://example.com/login", 0, 1),
                ("Home notice", "Shown on home", 2, 1, "http://example.com/home", 1, 1),
            ],
        )
        conn.execute(
            "DELETE FROM system_setting WHERE config_name IN ('system_application', 'disclaimer', 'web_about_description')"
        )
        conn.executemany(
            "INSERT INTO system_setting (config_name, config_value) VALUES (?, ?)",
            [
                ("system_application", json.dumps(application_setting, ensure_ascii=False)),
                ("disclaimer", "Seeded disclaimer"),
                ("web_about_description", "Seeded about description"),
            ],
        )
        conn.commit()


def normalize_value(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {k: normalize_value(v, key=k) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_value(item, key=key) for item in value]
    if isinstance(value, str):
        if value == ZERO_TIME:
            return value
        if key == "token" and value:
            return "<TOKEN>"
        if key == "referralCode" and value:
            return "<REFERRAL>"
        value = re.sub(r"/[0-9a-f]{32}(\.[a-z0-9]+)$", r"/<HASH>\1", value)
        value = value.replace("/tmp", "")
        if key in {"imageUrl", "iconUrl", "src", "path"}:
            return value
        if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value):
            return "<TIME>"
    return value


def assert_normalized_equal(go_value: Any, py_value: Any) -> None:
    assert normalize_value(go_value) == normalize_value(py_value)


def assert_monitor_shapes(go_resp: dict[str, Any], py_resp: dict[str, Any]) -> None:
    assert go_resp["code"] == py_resp["code"] == 0
    assert set(go_resp["data"].keys()) == set(py_resp["data"].keys())
    for key in go_resp["data"]:
        assert isinstance(py_resp["data"][key], type(go_resp["data"][key]))


def exercise_service(service: ServiceClient, favicon_page: str) -> dict[str, Any]:
    results: dict[str, Any] = {}

    results["about"] = service.post("/about")
    results["login_config"] = service.get("/openness/loginConfig")
    results["public_auth_before_public_user"] = service.post("/user/getAuthInfo")
    results["notice"] = service.post("/notice/getListByDisplayType", {"displayType": [1, 2]})

    login = service.post("/login", {"username": "admin@sun.cc", "password": "12345678"})
    results["login"] = login
    token = login["data"]["token"]

    results["invalid_login_token"] = service.post("/user/getInfo", token="bad-token")
    results["auth"] = service.post("/user/getAuthInfo", token=token)
    results["group_list_initial"] = service.post("/panel/itemIconGroup/getList", token=token)
    group_id = results["group_list_initial"]["data"]["list"][0]["id"]

    results["item_list_initial"] = service.post("/panel/itemIcon/getListByGroupId", {"itemIconGroupId": group_id}, token=token)
    results["module_get_initial"] = service.post("/system/moduleConfig/getByName", {"name": "deskModule"}, token=token)
    results["module_save"] = service.post("/system/moduleConfig/save", {"name": "deskModule", "value": {"visible": True}}, token=token)
    results["module_get_saved"] = service.post("/system/moduleConfig/getByName", {"name": "deskModule"}, token=token)
    results["user_config_get_initial"] = service.post("/panel/userConfig/get", token=token)
    results["user_config_set"] = service.post(
        "/panel/userConfig/set",
        {"panel": {"theme": "solid"}, "searchEngine": {"current": "bing"}},
        token=token,
    )
    results["user_config_get_saved"] = service.post("/panel/userConfig/get", token=token)

    item_payload = {
        "title": "Example",
        "url": "http://example.com",
        "lanUrl": "",
        "description": "desc",
        "openMethod": 1,
        "itemIconGroupId": group_id,
        "icon": {"itemType": 1, "src": "x", "text": "", "backgroundColor": "#fff"},
    }
    results["item_create"] = service.post("/panel/itemIcon/edit", item_payload, token=token)
    item_id = results["item_create"]["data"]["id"]
    results["item_add_multiple"] = service.post(
        "/panel/itemIcon/addMultiple",
        [
            {
                "title": "Extra 1",
                "url": "http://one.test",
                "lanUrl": "",
                "description": "",
                "openMethod": 0,
                "itemIconGroupId": group_id,
                "icon": {"itemType": 1, "src": "a", "text": "", "backgroundColor": "#000"},
            },
            {
                "title": "Extra 2",
                "url": "http://two.test",
                "lanUrl": "",
                "description": "",
                "openMethod": 0,
                "itemIconGroupId": group_id,
                "icon": {"itemType": 1, "src": "b", "text": "", "backgroundColor": "#111"},
            },
        ],
        token=token,
    )
    results["item_list_after_create"] = service.post("/panel/itemIcon/getListByGroupId", {"itemIconGroupId": group_id}, token=token)
    results["item_save_sort"] = service.post(
        "/panel/itemIcon/saveSort",
        {"itemIconGroupId": group_id, "sortItems": [{"id": item_id, "sort": 1}]},
        token=token,
    )
    results["group_create"] = service.post(
        "/panel/itemIconGroup/edit",
        {"title": "More", "icon": "i", "description": "desc"},
        token=token,
    )
    second_group_id = results["group_create"]["data"]["id"]
    results["group_save_sort"] = service.post(
        "/panel/itemIconGroup/saveSort",
        {"sortItems": [{"id": second_group_id, "sort": 2}]},
        token=token,
    )
    results["group_list_after_create"] = service.post("/panel/itemIconGroup/getList", token=token)

    results["get_referral_code"] = service.post("/user/getReferralCode", token=token)
    results["user_update_info"] = service.post("/user/updateInfo", {"name": "AdminUser", "headImage": "/x.png"}, token=token)
    results["user_get_info_after_update"] = service.post("/user/getInfo", token=token)

    results["favicon"] = service.post("/panel/itemIcon/getSiteFavicon", {"url": favicon_page}, token=token)
    results["upload_img"] = service.upload("/file/uploadImg", "imgfile", "tiny.png", PNG_1X1, "image/png", token=token)
    results["files_after_upload"] = service.post("/file/getList", token=token)
    uploaded_file_ids = [row["id"] for row in results["files_after_upload"]["data"]["list"]]
    results["file_deletes"] = service.post("/file/deletes", {"ids": uploaded_file_ids}, token=token)
    results["files_after_delete"] = service.post("/file/getList", token=token)

    results["users_create"] = service.post(
        "/panel/users/create",
        {"username": "user01", "password": "abc123", "name": "User01", "role": 2},
        token=token,
    )
    created_user_id = results["users_create"]["data"]["userId"]
    results["users_update"] = service.post(
        "/panel/users/update",
        {"id": created_user_id, "username": "user01", "password": "", "name": "UserRenamed", "role": 2},
        token=token,
    )
    results["users_list"] = service.post("/panel/users/getList", {"page": 1, "limit": 20, "keyword": ""}, token=token)
    results["public_user_set"] = service.post("/panel/users/setPublicVisitUser", {"userId": created_user_id}, token=token)
    results["public_user_get"] = service.post("/panel/users/getPublicVisitUser", token=token)
    results["public_auth_after_public_user"] = service.post("/user/getAuthInfo")
    results["public_auth_invalid_token"] = service.post("/user/getAuthInfo", token="bad-token")
    results["item_delete"] = service.post("/panel/itemIcon/deletes", {"ids": [item_id]}, token=token)
    results["group_delete"] = service.post("/panel/itemIconGroup/deletes", {"ids": [second_group_id]}, token=token)
    results["group_list_after_delete"] = service.post("/panel/itemIconGroup/getList", token=token)
    results["users_delete"] = service.post("/panel/users/deletes", {"userIds": [created_user_id]}, token=token)
    results["users_list_after_delete"] = service.post("/panel/users/getList", {"page": 1, "limit": 20, "keyword": ""}, token=token)

    results["update_password"] = service.post(
        "/user/updatePassword",
        {"oldPassword": "12345678", "newPassword": "87654321"},
        token=token,
    )
    results["user_get_info_after_password_change"] = service.post("/user/getInfo", token=token)
    results["relogin"] = service.post("/login", {"username": "admin@sun.cc", "password": "87654321"})

    relogin_token = results["relogin"]["data"]["token"]
    results["monitor_all"] = service.post("/system/monitor/getAll", token=relogin_token)
    results["monitor_cpu"] = service.post("/system/monitor/getCpuState", token=relogin_token)
    results["monitor_memory"] = service.post("/system/monitor/getMemonyState", token=relogin_token)
    results["monitor_mounts"] = service.post("/system/monitor/getDiskMountpoints", token=relogin_token)
    results["monitor_disk"] = service.post("/system/monitor/getDiskStateByPath", {"path": "/"}, token=relogin_token)

    return results


def exercise_full_service(service: ServiceClient, favicon_page: str) -> dict[str, Any]:
    seed_success_data(service)
    results: dict[str, Any] = {}

    results["static_index"] = service.root_get("/")
    results["static_asset"] = service.root_get("/assets/hello.txt")
    results["static_custom"] = service.root_get("/custom/theme.css")
    results["static_favicon_ico"] = service.root_get("/favicon.ico")
    results["static_favicon_svg"] = service.root_get("/favicon.svg")

    results["about"] = service.post("/about")
    results["login_config"] = service.get("/openness/loginConfig")
    results["disclaimer"] = service.get("/openness/getDisclaimer")
    results["about_description"] = service.get("/openness/getAboutDescription")
    results["notice"] = service.post("/notice/getListByDisplayType", {"displayType": [1, 2]})
    results["login_missing_password"] = service.post("/login", {"username": "admin@sun.cc"})

    admin_login = service.post("/login", {"username": "admin@sun.cc", "password": "12345678"})
    results["admin_login"] = admin_login
    admin_token = admin_login["data"]["token"]
    results["admin_get_info"] = service.post("/user/getInfo", token=admin_token)
    results["public_user_get_missing"] = service.post("/panel/users/getPublicVisitUser", token=admin_token)
    results["public_user_set_invalid"] = service.post("/panel/users/setPublicVisitUser", {"userId": 99999}, token=admin_token)
    results["upload_img_invalid"] = service.upload("/file/uploadImg", "imgfile", "bad.txt", b"bad", "text/plain", token=admin_token)
    results["item_edit_missing_group"] = service.post(
        "/panel/itemIcon/edit",
        {"title": "bad", "url": "http://example.com", "icon": {"itemType": 1, "src": "x", "text": "", "backgroundColor": "#fff"}},
        token=admin_token,
    )
    results["admin_group_list"] = service.post("/panel/itemIconGroup/getList", token=admin_token)

    results["users_create"] = service.post(
        "/panel/users/create",
        {"username": "user01", "password": "abc123", "name": "User01", "role": 2},
        token=admin_token,
    )
    created_user_id = results["users_create"]["data"]["userId"]
    results["users_list"] = service.post("/panel/users/getList", {"page": 1, "limit": 20, "keyword": ""}, token=admin_token)
    results["admin_delete_guard"] = service.post("/panel/users/deletes", {"userIds": [1, created_user_id]}, token=admin_token)

    user_login = service.post("/login", {"username": "user01", "password": "abc123"})
    results["user_login"] = user_login
    user_token = user_login["data"]["token"]
    results["user_get_info"] = service.post("/user/getInfo", token=user_token)
    results["user_group_list_initial"] = service.post("/panel/itemIconGroup/getList", token=user_token)
    user_group_id = results["user_group_list_initial"]["data"]["list"][0]["id"]

    results["module_save"] = service.post("/system/moduleConfig/save", {"name": "deskModule", "value": {"visible": True}}, token=user_token)
    results["module_get"] = service.post("/system/moduleConfig/getByName", {"name": "deskModule"}, token=user_token)
    results["user_config_set"] = service.post(
        "/panel/userConfig/set",
        {"panel": {"theme": "solid"}, "searchEngine": {"current": "bing"}},
        token=user_token,
    )
    results["user_config_get"] = service.post("/panel/userConfig/get", token=user_token)

    item_payload = {
        "title": "Example",
        "url": "http://example.com",
        "lanUrl": "",
        "description": "desc",
        "openMethod": 1,
        "itemIconGroupId": user_group_id,
        "icon": {"itemType": 1, "src": "x", "text": "", "backgroundColor": "#fff"},
    }
    results["item_create"] = service.post("/panel/itemIcon/edit", item_payload, token=user_token)
    item_id = results["item_create"]["data"]["id"]
    results["item_update"] = service.post(
        "/panel/itemIcon/edit",
        {
            "id": item_id,
            "title": "Example Updated",
            "url": "http://example.org",
            "lanUrl": "http://lan.example.org",
            "description": "updated",
            "openMethod": 0,
            "sort": 3,
            "itemIconGroupId": user_group_id,
            "icon": {"itemType": 1, "src": "y", "text": "", "backgroundColor": "#000"},
        },
        token=user_token,
    )
    results["item_add_multiple"] = service.post(
        "/panel/itemIcon/addMultiple",
        [
            {
                "title": "Extra 1",
                "url": "http://one.test",
                "lanUrl": "",
                "description": "",
                "openMethod": 0,
                "itemIconGroupId": user_group_id,
                "icon": {"itemType": 1, "src": "a", "text": "", "backgroundColor": "#000"},
            },
            {
                "title": "Extra 2",
                "url": "http://two.test",
                "lanUrl": "",
                "description": "",
                "openMethod": 0,
                "itemIconGroupId": user_group_id,
                "icon": {"itemType": 1, "src": "b", "text": "", "backgroundColor": "#111"},
            },
        ],
        token=user_token,
    )
    results["item_list"] = service.post("/panel/itemIcon/getListByGroupId", {"itemIconGroupId": user_group_id}, token=user_token)
    results["item_save_sort"] = service.post(
        "/panel/itemIcon/saveSort",
        {"itemIconGroupId": user_group_id, "sortItems": [{"id": item_id, "sort": 1}]},
        token=user_token,
    )
    results["group_create"] = service.post(
        "/panel/itemIconGroup/edit",
        {"title": "More", "icon": "i", "description": "desc"},
        token=user_token,
    )
    second_group_id = results["group_create"]["data"]["id"]
    results["group_update"] = service.post(
        "/panel/itemIconGroup/edit",
        {"id": second_group_id, "title": "More Updated", "icon": "i2", "description": "desc2", "sort": 2},
        token=user_token,
    )
    results["group_save_sort"] = service.post(
        "/panel/itemIconGroup/saveSort",
        {"sortItems": [{"id": second_group_id, "sort": 2}]},
        token=user_token,
    )
    results["group_list"] = service.post("/panel/itemIconGroup/getList", token=user_token)
    all_group_ids = [row["id"] for row in results["group_list"]["data"]["list"]]
    results["group_delete_guard"] = service.post("/panel/itemIconGroup/deletes", {"ids": all_group_ids}, token=user_token)

    results["get_referral_code"] = service.post("/user/getReferralCode", token=user_token)
    results["user_update_info"] = service.post("/user/updateInfo", {"name": "UserRenamed", "headImage": "/x.png"}, token=user_token)
    results["favicon"] = service.post("/panel/itemIcon/getSiteFavicon", {"url": favicon_page}, token=user_token)
    results["upload_img"] = service.upload("/file/uploadImg", "imgfile", "tiny.png", PNG_1X1, "image/png", token=user_token)
    results["upload_files"] = service.upload_many(
        "/file/uploadFiles",
        [
            ("files[]", "a.txt", b"A", "text/plain"),
            ("files[]", "b.txt", b"B", "text/plain"),
        ],
        token=user_token,
    )
    results["files_after_upload"] = service.post("/file/getList", token=user_token)
    uploaded_paths = [row["src"] for row in results["files_after_upload"]["data"]["list"]]
    results["uploaded_fetch"] = [service.root_get(path).content for path in uploaded_paths]
    uploaded_file_ids = [row["id"] for row in results["files_after_upload"]["data"]["list"]]
    results["file_deletes"] = service.post("/file/deletes", {"ids": uploaded_file_ids}, token=user_token)
    results["files_after_delete"] = service.post("/file/getList", token=user_token)

    results["public_user_set"] = service.post("/panel/users/setPublicVisitUser", {"userId": created_user_id}, token=admin_token)
    results["public_user_get"] = service.post("/panel/users/getPublicVisitUser", token=admin_token)
    results["public_auth"] = service.post("/user/getAuthInfo")
    results["public_group_list"] = service.post("/panel/itemIconGroup/getList")
    results["public_item_list"] = service.post("/panel/itemIcon/getListByGroupId", {"itemIconGroupId": user_group_id})
    results["public_user_config_get"] = service.post("/panel/userConfig/get")
    results["public_module_get"] = service.post("/system/moduleConfig/getByName", {"name": "deskModule"})
    results["monitor_all"] = service.post("/system/monitor/getAll")
    results["monitor_cpu"] = service.post("/system/monitor/getCpuState")
    results["monitor_memory"] = service.post("/system/monitor/getMemonyState")
    results["monitor_mounts"] = service.post("/system/monitor/getDiskMountpoints", token=user_token)
    results["monitor_disk"] = service.post("/system/monitor/getDiskStateByPath", {"path": "/"})

    results["item_delete"] = service.post("/panel/itemIcon/deletes", {"ids": [item_id]}, token=user_token)
    results["group_delete"] = service.post("/panel/itemIconGroup/deletes", {"ids": [second_group_id]}, token=user_token)
    results["users_update"] = service.post(
        "/panel/users/update",
        {"id": created_user_id, "username": "user01", "password": "", "name": "UserRenamed", "role": 2},
        token=admin_token,
    )
    results["user_update_password"] = service.post(
        "/user/updatePassword",
        {"oldPassword": "abc123", "newPassword": "abc12345"},
        token=user_token,
    )
    results["user_get_info_after_password_change"] = service.post("/user/getInfo", token=user_token)
    results["user_relogin"] = service.post("/login", {"username": "user01", "password": "abc12345"})
    results["users_delete"] = service.post("/panel/users/deletes", {"userIds": [created_user_id]}, token=admin_token)
    results["users_list_after_delete"] = service.post("/panel/users/getList", {"page": 1, "limit": 20, "keyword": ""}, token=admin_token)
    results["logout"] = service.post("/logout", token=admin_token)
    results["admin_get_info_after_logout"] = service.post("/user/getInfo", token=admin_token)

    return results


def assert_python_full_results(results: dict[str, Any], service: ServiceClient) -> None:
    assert results["static_index"].status_code == 200
    assert results["static_index"].text == "<!doctype html><html><body>sun-panel test</body></html>"
    assert results["static_asset"].text == "asset-ok\n"
    assert results["static_custom"].text == "body{background:#fff;}\n"
    assert results["static_favicon_ico"].content == PNG_1X1
    assert results["static_favicon_svg"].content == SVG_ICON

    assert results["about"]["code"] == 0
    assert results["about"]["data"]["versionName"] == "1.3.0"
    assert results["login_config"]["code"] == 0
    assert results["login_config"]["data"]["loginCaptcha"] is True
    assert results["login_config"]["data"]["register"]["openRegister"] is True
    assert results["disclaimer"] == {"code": 0, "msg": "OK", "data": "Seeded disclaimer"}
    assert results["about_description"] == {"code": 0, "msg": "OK", "data": "Seeded about description"}
    assert results["notice"]["code"] == 0
    assert len(results["notice"]["data"]["list"]) == 2
    assert results["login_missing_password"]["code"] == -1
    assert "Password" in results["login_missing_password"]["msg"]

    assert results["admin_login"]["code"] == 0
    assert results["admin_get_info"]["code"] == 0
    assert results["public_user_get_missing"]["code"] == -1
    assert results["public_user_set_invalid"]["code"] == -1
    assert results["upload_img_invalid"]["code"] == 1301
    assert results["item_edit_missing_group"]["code"] == -1
    assert results["admin_group_list"]["code"] == 0
    assert len(results["admin_group_list"]["data"]["list"]) == 1

    assert results["users_create"]["code"] == 0
    assert results["users_list"]["code"] == 0
    assert len(results["users_list"]["data"]["list"]) == 2
    assert results["admin_delete_guard"]["code"] == 1201

    assert results["user_login"]["code"] == 0
    assert results["user_get_info"]["code"] == 0
    assert results["user_group_list_initial"]["code"] == 0
    assert len(results["user_group_list_initial"]["data"]["list"]) == 1

    assert results["module_save"]["code"] == 0
    assert results["module_get"]["code"] == 0
    assert results["module_get"]["data"] == {"visible": True}
    assert results["user_config_set"]["code"] == 0
    assert results["user_config_get"]["code"] == 0
    assert results["user_config_get"]["data"]["panel"] == {"theme": "solid"}

    assert results["item_create"]["code"] == 0
    assert results["item_update"]["code"] == 0
    assert results["item_add_multiple"]["code"] == 0
    assert len(results["item_add_multiple"]["data"]) == 2
    assert results["item_list"]["code"] == 0
    assert len(results["item_list"]["data"]["list"]) == 3
    assert results["item_save_sort"]["code"] == 0
    assert results["group_create"]["code"] == 0
    assert results["group_update"]["code"] == 0
    assert results["group_save_sort"]["code"] == 0
    assert results["group_list"]["code"] == 0
    assert len(results["group_list"]["data"]["list"]) == 2
    assert results["group_delete_guard"]["code"] == 1201

    assert results["get_referral_code"]["code"] == 0
    assert len(results["get_referral_code"]["data"]["referralCode"]) == 8
    assert results["user_update_info"]["code"] == 0
    assert results["favicon"]["code"] == 0
    assert results["upload_img"]["code"] == 0
    assert results["upload_files"]["code"] == 0
    assert results["upload_files"]["data"]["errFiles"] == []
    assert set(results["upload_files"]["data"]["succMap"].keys()) == {"a.txt", "b.txt"}
    assert results["files_after_upload"]["code"] == 0
    assert len(results["files_after_upload"]["data"]["list"]) >= 3
    assert all(content for content in results["uploaded_fetch"])
    assert results["file_deletes"]["code"] == 0
    assert results["files_after_delete"]["code"] == 0
    assert results["files_after_delete"]["data"]["count"] == 0

    assert results["public_user_set"]["code"] == 0
    assert results["public_user_get"]["code"] == 0
    assert results["public_auth"]["code"] == 0
    assert results["public_auth"]["data"]["visitMode"] == 1
    assert results["public_group_list"]["code"] == 0
    assert results["public_item_list"]["code"] == 0
    assert results["public_user_config_get"]["code"] == 0
    assert results["public_module_get"]["code"] == 0

    assert results["monitor_all"]["code"] == -1
    assert results["monitor_cpu"]["code"] == 0
    assert results["monitor_memory"]["code"] == 0
    assert results["monitor_mounts"]["code"] == 0
    assert len(results["monitor_mounts"]["data"]) > 0
    assert results["monitor_disk"]["code"] == 0

    assert results["item_delete"]["code"] == 0
    assert results["group_delete"]["code"] == 0
    assert results["users_update"]["code"] == 0
    assert results["user_update_password"]["code"] == 1001
    assert results["user_get_info_after_password_change"]["code"] == 1001
    assert results["user_relogin"]["code"] == 1003
    assert results["users_delete"]["code"] == 0
    assert results["users_list_after_delete"]["code"] == 0
    assert len(results["users_list_after_delete"]["data"]["list"]) == 1
    assert results["logout"]["code"] == 0
    assert results["admin_get_info_after_logout"]["code"] == 1001

    assert ALL_API_ROUTES.issubset(service.api_hits)
    assert STATIC_ROUTES.issubset(service.static_hits)


def test_python_backend_full_functional_suite() -> None:
    with local_site() as favicon_page, running_python_service(43203) as py:
        try:
            results = exercise_full_service(py, favicon_page)
            assert_python_full_results(results, py)
        finally:
            py.close()


@pytest.mark.skipif(not GO_PARITY_ENABLED, reason="set SUN_PANEL_ENABLE_GO_PARITY=1 to run Go parity tests")
def test_go_and_python_backend_parity() -> None:
    with local_site() as favicon_page, running_go_service(43002) as go, running_python_service(43003) as py:
        try:
            go_results = exercise_service(go, favicon_page)
            py_results = exercise_service(py, favicon_page)
        finally:
            go.close()
            py.close()

    exact_keys = [
        "about",
        "login_config",
        "public_auth_before_public_user",
        "notice",
        "login",
        "invalid_login_token",
        "auth",
        "group_list_initial",
        "item_list_initial",
        "module_get_initial",
        "module_save",
        "module_get_saved",
        "user_config_get_initial",
        "user_config_set",
        "user_config_get_saved",
        "item_create",
        "item_add_multiple",
        "item_list_after_create",
        "item_save_sort",
        "group_create",
        "group_save_sort",
        "group_list_after_create",
        "get_referral_code",
        "user_update_info",
        "user_get_info_after_update",
        "favicon",
        "upload_img",
        "files_after_upload",
        "file_deletes",
        "files_after_delete",
        "users_create",
        "users_update",
        "users_list",
        "public_user_set",
        "public_user_get",
        "public_auth_after_public_user",
        "public_auth_invalid_token",
        "item_delete",
        "group_delete",
        "group_list_after_delete",
        "users_delete",
        "users_list_after_delete",
        "update_password",
        "user_get_info_after_password_change",
        "relogin",
        "monitor_all",
    ]

    for key in exact_keys:
        assert_normalized_equal(go_results[key], py_results[key])

    assert_monitor_shapes(go_results["monitor_cpu"], py_results["monitor_cpu"])
    assert_monitor_shapes(go_results["monitor_memory"], py_results["monitor_memory"])
    assert go_results["monitor_mounts"]["code"] == py_results["monitor_mounts"]["code"] == 0
    assert len(go_results["monitor_mounts"]["data"]) > 0
    assert len(py_results["monitor_mounts"]["data"]) > 0
    assert set(go_results["monitor_mounts"]["data"][0].keys()) == set(py_results["monitor_mounts"]["data"][0].keys())
    assert go_results["monitor_disk"]["code"] == py_results["monitor_disk"]["code"] == 0
    assert set(go_results["monitor_disk"]["data"].keys()) == set(py_results["monitor_disk"]["data"].keys())


@pytest.mark.skipif(not GO_PARITY_ENABLED, reason="set SUN_PANEL_ENABLE_GO_PARITY=1 to run Go parity tests")
def test_go_and_python_full_functional_suite() -> None:
    with local_site() as favicon_page, running_go_service(43102) as go, running_python_service(43103) as py:
        try:
            go_results = exercise_full_service(go, favicon_page)
            py_results = exercise_full_service(py, favicon_page)
        finally:
            go.close()
            py.close()

    exact_keys = [
        "about",
        "login_config",
        "disclaimer",
        "about_description",
        "notice",
        "login_missing_password",
        "admin_login",
        "admin_get_info",
        "public_user_get_missing",
        "public_user_set_invalid",
        "upload_img_invalid",
        "item_edit_missing_group",
        "admin_group_list",
        "users_create",
        "users_list",
        "admin_delete_guard",
        "user_login",
        "user_get_info",
        "user_group_list_initial",
        "module_save",
        "module_get",
        "user_config_set",
        "user_config_get",
        "item_create",
        "item_update",
        "item_add_multiple",
        "item_list",
        "item_save_sort",
        "group_create",
        "group_update",
        "group_save_sort",
        "group_list",
        "group_delete_guard",
        "get_referral_code",
        "user_update_info",
        "favicon",
        "upload_img",
        "upload_files",
        "files_after_upload",
        "file_deletes",
        "files_after_delete",
        "public_user_set",
        "public_user_get",
        "public_auth",
        "public_group_list",
        "public_item_list",
        "public_user_config_get",
        "public_module_get",
        "monitor_all",
        "item_delete",
        "group_delete",
        "users_update",
        "users_delete",
        "users_list_after_delete",
        "user_update_password",
        "user_get_info_after_password_change",
        "user_relogin",
        "logout",
        "admin_get_info_after_logout",
    ]

    for key in exact_keys:
        assert_normalized_equal(go_results[key], py_results[key])

    assert go_results["static_index"].status_code == py_results["static_index"].status_code == 200
    assert go_results["static_index"].text == py_results["static_index"].text == "<!doctype html><html><body>sun-panel test</body></html>"
    assert go_results["static_asset"].text == py_results["static_asset"].text == "asset-ok\n"
    assert go_results["static_custom"].text == py_results["static_custom"].text == "body{background:#fff;}\n"
    assert go_results["static_favicon_ico"].content == py_results["static_favicon_ico"].content == PNG_1X1
    assert go_results["static_favicon_svg"].content == py_results["static_favicon_svg"].content == SVG_ICON
    assert go_results["uploaded_fetch"] == py_results["uploaded_fetch"]

    assert_monitor_shapes(go_results["monitor_cpu"], py_results["monitor_cpu"])
    assert_monitor_shapes(go_results["monitor_memory"], py_results["monitor_memory"])
    assert go_results["monitor_mounts"]["code"] == py_results["monitor_mounts"]["code"] == 0
    assert len(go_results["monitor_mounts"]["data"]) > 0
    assert len(py_results["monitor_mounts"]["data"]) > 0
    assert set(go_results["monitor_mounts"]["data"][0].keys()) == set(py_results["monitor_mounts"]["data"][0].keys())
    assert go_results["monitor_disk"]["code"] == py_results["monitor_disk"]["code"] == 0
    assert set(go_results["monitor_disk"]["data"].keys()) == set(py_results["monitor_disk"]["data"].keys())

    assert ALL_API_ROUTES.issubset(go.api_hits)
    assert ALL_API_ROUTES.issubset(py.api_hits)
    assert STATIC_ROUTES.issubset(go.static_hits)
    assert STATIC_ROUTES.issubset(py.static_hits)
