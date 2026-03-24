"""
CLI Server — 基于 FastAPI 的内嵌 HTTP Server

主程序启动时在后台线程中启动，CLI 客户端通过此 Server 与主程序交互。
- 启动时将 port + token 写入临时文件
- 提供 /api/health 健康检查接口
- 提供 /api/status 状态查询接口
- 提供各模块 API 端点
"""
import asyncio
import logging
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from ops_toolkit.app import App

logger = logging.getLogger("ops_toolkit.cli_server")

# 临时文件路径
_SERVER_INFO_FILE = Path(__file__).parent.parent.parent.joinpath(
    "py_ops_toolkit_server.info"
)


def get_server_info_path() -> Path:
    """获取 Server 信息文件路径（优先使用系统临时目录）"""
    import tempfile
    return Path(tempfile.gettempdir()).joinpath("py_ops_toolkit_server.info")


def save_server_info(port: int, token: str):
    """将 Server 信息写入临时文件"""
    _SERVER_INFO_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SERVER_INFO_FILE.write_text(f"{port}\n{token}", encoding="utf-8")
    logger.info(f"Server info saved to {_SERVER_INFO_FILE}")


def load_server_info() -> dict | None:
    """从临时文件加载 Server 信息"""
    path = get_server_info_path()
    if not path.exists():
        # 尝试项目根目录下的路径
        if not _SERVER_INFO_FILE.exists():
            return None
        path = _SERVER_INFO_FILE

    try:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        return {"port": int(lines[0]), "token": lines[1]}
    except (IndexError, ValueError, FileNotFoundError) as e:
        logger.debug(f"Failed to load server info: {e}")
        return None


def clear_server_info():
    """清理 Server 信息文件"""
    for p in [get_server_info_path(), _SERVER_INFO_FILE]:
        if p.exists():
            try:
                p.unlink()
                logger.debug(f"Server info file removed: {p}")
            except OSError:
                pass


# ============ FastAPI App ============

app_instance: FastAPI | None = None
_app_ref: "App | None" = None
_server_token: str = ""


def create_app(app_ref: "App | None" = None) -> FastAPI:
    """创建 FastAPI 应用实例"""
    global app_instance, _app_ref, _server_token

    _app_ref = app_ref
    _server_token = secrets.token_hex(16)

    @asynccontextmanager
    async def lifespan(fastapi_app: FastAPI):
        logger.info("CLI Server starting...")
        yield
        logger.info("CLI Server shutting down...")

    app_instance = FastAPI(
        title="ops-toolkit CLI Server",
        description="ops-toolkit 主程序内嵌 API Server",
        version="1.0.0",
        lifespan=lifespan,
    )

    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============ 认证中间件 ============
    @app_instance.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if request.url.path == "/api/health":
            return await call_next(request)
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token or token != _server_token:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return await call_next(request)

    # ============ 健康检查 ============
    @app_instance.get("/api/health")
    async def health():
        return {"status": "ok"}

    # ============ 主程序状态 ============
    @app_instance.get("/api/status")
    async def get_status():
        if _app_ref is None:
            return {"error": "App not initialized"}
        from ops_toolkit import VERSION
        return {
            "version": VERSION,
            "app_name": _app_ref.app_name,
            "running": not _app_ref.exited,
            "components": {
                "keepalive": _app_ref.keepalive.is_running(),
                "hourly_reminder": _app_ref.hourly_reminder.is_active,
                "monitor_clipboard": _app_ref.monitor_clipboard.started,
            },
        }

    @app_instance.post("/api/quit")
    async def quit_app():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        if _app_ref.exited:
            raise HTTPException(status_code=400, detail="App already exited")
        _app_ref.exit_flag = True
        return {"message": "Quit signal sent"}

    # ============ 配置管理 ============
    @app_instance.get("/api/config")
    async def config_show():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        cfg = _app_ref.config
        return {
            "app_name": cfg.app_name,
            "startup": cfg.startup,
            "update_beta": cfg.update_beta,
            "hotkey_translate": cfg.hotkey_translate,
            "hotkey_todo_create": cfg.hotkey_todo_create,
            "hotkey_todo_display": cfg.hotkey_todo_display,
            "registry": cfg.registry,
            "config_path": str(cfg.config_path),
            "data_dir": str(cfg.data_dir),
            "log_path": str(cfg.log_path),
        }

    @app_instance.get("/api/config/{key:path}")
    async def config_get(key: str):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        cfg = _app_ref.config
        value = getattr(cfg, key, None)
        if value is None:
            raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
        return {"key": key, "value": str(value)}

    @app_instance.put("/api/config/{key:path}")
    async def config_set(key: str, request: Request):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        body = await request.json()
        value = body.get("value")
        if value is None:
            raise HTTPException(status_code=400, detail="Missing 'value' in request body")
        cfg = _app_ref.config
        if not hasattr(cfg, key):
            raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
        setattr(cfg, key, value)
        try:
            cfg.save()
            return {"message": f"Config '{key}' updated and saved", "value": str(value)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")

    # ============ 待办事项 ============
    @app_instance.get("/api/todo/list")
    async def todo_list(status: int | None = None, limit: int = 50):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        from ops_toolkit.todolist.models import DBManager
        db = DBManager(_app_ref.config.data_dir)
        tasks = db.get_tasks(status=status, limit=limit)
        return {
            "tasks": [
                {**t.to_dict(), "create_time": str(t.create_time or ""), "do_time": str(t.do_time or "")}
                for t in tasks
            ]
        }

    @app_instance.get("/api/todo/{task_id}")
    async def todo_get(task_id: int):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        from ops_toolkit.todolist.models import DBManager
        db = DBManager(_app_ref.config.data_dir)
        task = db.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return {**task.to_dict(), "create_time": str(task.create_time or ""), "do_time": str(task.do_time or "")}

    @app_instance.post("/api/todo")
    async def todo_add(request: Request):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        body = await request.json()
        title = body.get("title")
        if not title:
            raise HTTPException(status_code=400, detail="Missing 'title'")
        from ops_toolkit.todolist.models import DBManager
        db = DBManager(_app_ref.config.data_dir)
        task = db.add_task(
            title=title,
            desc=body.get("desc"),
            link=body.get("link"),
            do_time=body.get("do_time"),
        )
        return {"message": "Task created", "id": task.id}

    @app_instance.put("/api/todo/{task_id}")
    async def todo_update(task_id: int, request: Request):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        body = await request.json()
        from ops_toolkit.todolist.models import DBManager
        db = DBManager(_app_ref.config.data_dir)
        task = db.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        update_fields = {}
        for key in ["title", "desc", "link", "do_time", "status"]:
            if key in body:
                update_fields[key] = body[key]
        if update_fields:
            db.update_task(task_id, **update_fields)
        return {"message": f"Task {task_id} updated"}

    @app_instance.delete("/api/todo/{task_id}")
    async def todo_delete(task_id: int):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        from ops_toolkit.todolist.models import DBManager
        db = DBManager(_app_ref.config.data_dir)
        db.update_task(task_id, status=2)
        return {"message": f"Task {task_id} deleted"}

    # ============ 组件控制 ============
    @app_instance.get("/api/keepalive/status")
    async def keepalive_status():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        return {"running": _app_ref.keepalive.is_running()}

    @app_instance.post("/api/keepalive/on")
    async def keepalive_on():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        _app_ref.keepalive.start()
        return {"message": "Keepalive started"}

    @app_instance.post("/api/keepalive/off")
    async def keepalive_off():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        _app_ref.keepalive.stop()
        return {"message": "Keepalive stopped"}

    @app_instance.get("/api/reminder/status")
    async def reminder_status():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        return {"active": _app_ref.hourly_reminder.is_active, "next_hour": _app_ref.hourly_reminder.next_hour}

    @app_instance.post("/api/reminder/on")
    async def reminder_on(after: int = 1):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        _app_ref.hourly_reminder.start(after=after)
        return {"message": "Hourly reminder started", "next_hour": _app_ref.hourly_reminder.next_hour}

    @app_instance.post("/api/reminder/off")
    async def reminder_off():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        _app_ref.hourly_reminder.stop()
        return {"message": "Hourly reminder stopped"}

    @app_instance.get("/api/clipboard/status")
    async def clipboard_status():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        return {"running": _app_ref.monitor_clipboard.started, "auto_sls": _app_ref.monitor_clipboard.auto_sls_split}

    @app_instance.post("/api/clipboard/on")
    async def clipboard_on():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        _app_ref.monitor_clipboard.start()
        return {"message": "Clipboard monitoring started"}

    @app_instance.post("/api/clipboard/off")
    async def clipboard_off():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        _app_ref.monitor_clipboard.stop()
        return {"message": "Clipboard monitoring stopped"}

    @app_instance.post("/api/clipboard/auto-sls/on")
    async def clipboard_auto_sls_on():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        _app_ref.monitor_clipboard.auto_sls_split = True
        return {"message": "Auto SLS split enabled"}

    @app_instance.post("/api/clipboard/auto-sls/off")
    async def clipboard_auto_sls_off():
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        _app_ref.monitor_clipboard.auto_sls_split = False
        return {"message": "Auto SLS split disabled"}

    @app_instance.get("/api/clipboard/history")
    async def clipboard_history(limit: int = 50):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        session = _app_ref.monitor_clipboard._get_session()
        try:
            records = (
                session.query(_app_ref.monitor_clipboard.ClipboardRecord)
                .order_by(_app_ref.monitor_clipboard.ClipboardRecord.time.desc())
                .limit(limit)
                .all()
            )
            return {
                "records": [
                    {"id": r.id, "time": str(r.time), "type": r.typ, "text": r.text}
                    for r in records
                ]
            }
        finally:
            session.close()

    # ============ 翻译 ============
    @app_instance.post("/api/translate")
    async def translate_text(request: Request):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        body = await request.json()
        text = body.get("text")
        if not text:
            raise HTTPException(status_code=400, detail="Missing 'text'")
        try:
            from ops_toolkit.translate.main import Translater
            translater = _app_ref.translater
            result = translater.translate(text)
            return {"text": text, "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Translation failed: {e}")

    @app_instance.get("/api/translate/history")
    async def translate_history(limit: int = 50):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        try:
            records = _app_ref.history_manager.get_records(limit=limit)
            return {"records": records}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get history: {e}")

    # ============ 通知 ============
    @app_instance.post("/api/notify")
    async def send_notify(request: Request):
        if _app_ref is None:
            raise HTTPException(status_code=500, detail="App not initialized")
        body = await request.json()
        title = body.get("title", "")
        message = body.get("message", "")
        try:
            from ops_toolkit.tools import toolkit_notify
            toolkit_notify(title=title, message=message)
            return {"message": "Notification sent"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send notification: {e}")

    return app_instance


class CLIServer:
    """CLI Server 管理器，负责启动/停止 FastAPI Server"""

    def __init__(self, app_ref: "App | None" = None, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.app_ref = app_ref
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._token: str = ""

    def start(self):
        """在后台线程中启动 Server"""
        global _server_token

        # 创建 FastAPI app（同时设置模块级 _server_token）
        fastapi_app = create_app(self.app_ref)
        self._token = _server_token

        config = uvicorn.Config(
            app=fastapi_app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)

        self._thread = threading.Thread(target=self._run, daemon=True, name="cli-server")
        self._thread.start()

        # 等待 Server 启动，获取实际端口
        for _ in range(50):
            if self._server.started:
                break
            time.sleep(0.1)

        # 获取实际端口
        # uvicorn.Config 的 port 如果为 0，会自动分配
        servers = self._server.servers
        if servers:
            self.port = servers[0].sockets[0].getsockname()[1]

        save_server_info(self.port, self._token)
        logger.info(f"CLI Server started on {self.host}:{self.port}")

    def _run(self):
        """在后台线程中运行 Server"""
        try:
            asyncio.run(self._server.serve())
        except Exception as e:
            logger.error(f"CLI Server error: {e}")

    def stop(self):
        """停止 Server"""
        if self._server:
            self._server.should_exit = True
            logger.info("CLI Server stop signal sent")
        clear_server_info()

    @property
    def token(self) -> str:
        return self._token
