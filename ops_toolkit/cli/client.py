"""
CLI 客户端 — 连接主程序 CLI Server 的 HTTP Client
"""
import logging
from pathlib import Path
from typing import Any

import requests

from ops_toolkit.cli_server import load_server_info, clear_server_info

logger = logging.getLogger("ops_toolkit.cli.client")

DEFAULT_TIMEOUT = 10


class CLIClientError(Exception):
    """CLI 客户端异常"""
    pass


class ServerNotRunningError(CLIClientError):
    """主程序未运行"""
    pass


class AuthError(CLIClientError):
    """认证失败"""
    pass


class CLIClient:
    """CLI HTTP 客户端"""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self._base_url: str = ""
        self._token: str = ""
        self._session = requests.Session()

    def _load_connection(self):
        """从临时文件加载连接信息"""
        info = load_server_info()
        if info is None:
            raise ServerNotRunningError("主程序未运行，请先启动主程序。")
        self._base_url = f"http://127.0.0.1:{info['port']}"
        self._token = info["token"]

    def _request(self, method: str, path: str, json_data: dict | None = None, **kwargs) -> dict:
        """发送 HTTP 请求"""
        self._load_connection()

        url = f"{self._base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"
        headers["Content-Type"] = "application/json"
        kwargs.setdefault("timeout", self.timeout)
        if json_data is not None:
            kwargs.setdefault("json", json_data)

        try:
            resp = self._session.request(method, url, headers=headers, **kwargs)
        except requests.ConnectionError:
            raise ServerNotRunningError("无法连接到主程序，请确认主程序已启动。")

        if resp.status_code == 401:
            clear_server_info()
            raise AuthError("认证失败，Server Token 无效。")

        if resp.status_code == 404:
            try:
                data = resp.json()
                raise CLIClientError(data.get("detail", f"Not found: {path}"))
            except ValueError:
                raise CLIClientError(f"Not found: {path}")

        if resp.status_code >= 400:
            try:
                data = resp.json()
                raise CLIClientError(data.get("detail", f"Error {resp.status_code}: {path}"))
            except ValueError:
                raise CLIClientError(f"Error {resp.status_code}: {path}")

        return resp.json()

    def get(self, path: str, **kwargs) -> dict:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, json_data: dict | None = None, **kwargs) -> dict:
        return self._request("POST", path, json_data=json_data, **kwargs)

    def put(self, path: str, json_data: dict | None = None, **kwargs) -> dict:
        return self._request("PUT", path, json_data=json_data, **kwargs)

    def delete(self, path: str, **kwargs) -> dict:
        return self._request("DELETE", path, **kwargs)

    def check_health(self) -> bool:
        """检查主程序是否运行"""
        info = load_server_info()
        if info is None:
            return False
        try:
            url = f"http://127.0.0.1:{info['port']}/api/health"
            resp = requests.get(url, timeout=3)
            return resp.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            clear_server_info()
            return False
