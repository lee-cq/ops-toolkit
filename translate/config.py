"""
配置文件处理

1. 公开配置
2. API秘钥
"""
import os
import sys
import winreg
from logging import getLogger
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import field_serializer

from translate.api_abs import TranslateApiAbs

logger = getLogger("translate.config")


class TranslateApiModel(BaseModel):
    api_type: str
    text: tuple[int, int] = [0, 0]
    image: tuple[int, int] = [0, 0]
    auth: tuple[str, str]

    # noinspection PyAttributeOutsideInit
    def model_post_init(self, context: Any, /) -> None:
        self._api = self.api_factory()

    @property
    def api(self):
        return self._api

    def api_factory(self) -> TranslateApiAbs:
        if self.api_type == "baidu":
            from translate.api_baidu import TranslateApiBaidu
            return TranslateApiBaidu(self.auth, self)
        elif self.api_type == "aliyun":
            from translate.api_aliyun import TranslateApiAliyun
            return TranslateApiAliyun(self.auth, self)
        elif self.api_type == "tencent":
            from translate.api_tencent import TranslateApiTencent
            return TranslateApiTencent(self.auth, self)
        raise NotImplementedError


class FeishuApiModel(BaseModel):
    """"""
    app_id: str = ""
    app_secret: str = ""

    app_token: str = ""  # 飞书多维表格Token
    table_id: str = ""

    last_post_id: int = 0


class Config(BaseModel):
    apis: list[TranslateApiModel] = []
    feishu: FeishuApiModel | None = FeishuApiModel()
    app_name: str = "translate"
    startup: bool = False
    hotkey: str = '<ctrl>+<alt>+d'

    config_path: Path
    data_dir: Path = None
    translation_history_path: Path = None
    log_path: Path = None

    @field_serializer("data_dir", "translation_history_path", "log_path", "config_path")
    def serialize_path(self, v: Path) -> str:
        return v.as_posix()

    def save(self):
        self.set_startup()
        with self.config_path.open("w") as f:
            if self.config_path.suffix == ".json":
                from json import dump
                dump(self.model_dump(), f, ensure_ascii=False, indent=2)
            elif self.config_path.suffix == ".toml":
                from toml import dump
                dump(self.model_dump(), f)
            else:
                logger.error("config file format error, %s", self.config_path)
                raise ValueError(f"config file format error, {self.config_path=}")
            logger.info("save config to %s", self.config_path)

    def model_post_init(self, context: Any, /) -> None:
        if self.data_dir is None:
            self.data_dir = self.config_path.parent

        if self.translation_history_path is None:
            self.translation_history_path = self.data_dir.joinpath("translation_history.db")

        if self.log_path is None:
            self.log_path = self.data_dir.joinpath(f"{self.app_name.lower()}.log")

        if self.startup:
            self.set_startup()

        self.config_path = self.config_path.absolute()
        self.data_dir = self.data_dir.absolute()
        self.translation_history_path = self.translation_history_path.absolute()
        self.log_path = self.log_path.absolute()

        self.data_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(self.data_dir)

    def set_startup(self):
        """设置开机自启"""

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                 winreg.KEY_SET_VALUE)
            if self.startup:
                if sys.argv[0].endswith(".exe"):
                    winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, f"{sys.argv[0]}")
                    logger.info(f"设置开机自启成功[exe]: {self.app_name}: {sys.argv[0]}")
                else:
                    winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, f"{sys.executable} {sys.argv[0]}")
                    logger.info(f"设置开机自启成功[py]: {self.app_name}: {sys.executable} {sys.argv[0]}")
            else:
                winreg.DeleteValue(key, self.app_name)
                logger.info(f"删除开机自启成功: {self.app_name}")
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"设置开机自启失败: {e}")

    @property
    def api(self):
        """"""
        return self.apis[0].api


def find_config_path() -> Path:
    """查找配置文件路径
    1. 环境变量 TRANSLATE_CONFIG_PATH
    2. 当前用户主目录下的 .translate_config.toml 或 .translate_config.json
    3. 当前目录下的 translate_config.toml 或 translate_config.json
    4. 当前目录下的 _lo_config.toml 或 _lo_config.json
    5. 在当前目录下创建 translate_config.toml 或 translate_config.json
    """
    import os
    from pathlib import Path

    # 1. 检查环境变量
    env_path = os.getenv("TRANSLATE_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    # 2. 检查用户主目录
    home_dir = Path.home()
    for filename in [".config/translate/config.toml", ".config/translate/config.json"]:
        config_path = home_dir / filename
        if config_path.exists():
            return config_path

    # 3. 检查当前目录下的 translate_config 文件
    current_dir = Path.cwd()
    for filename in ["translate/config.toml", "translate/config.json", "_lo_config.toml", "_lo_config.json"]:
        config_path = current_dir / filename
        if config_path.exists():
            return config_path

    # 5. 在当前目录下创建默认配置文件 (使用toml格式)
    default_config = home_dir / ".config/translate/config.toml"
    default_config.parent.mkdir(parents=True, exist_ok=True)
    default_config.touch()
    return default_config.absolute()


def load_config(path: str = "") -> Config:
    if not path:
        path = find_config_path()

    p = Path(path)
    logger.info(f"load config from {p=}")
    print(f"load config from {p.absolute()}")

    _config = {"config_path": p}
    if not p.exists():
        print(f"config file not exists, create at {p}")
        _c = Config.model_validate(_config)
        _c.save()
        return _c

    if p.suffix == '.json':
        from json import load
        _config.update(load(p.open("rb")))
    elif p.suffix == ".toml":
        from tomllib import load
        _config.update(load(p.open("rb")))
    else:
        raise ValueError(f"config file format error, {p=}")

    return Config.model_validate(_config)


config = load_config()

if __name__ == '__main__':
    print(config.model_dump_json(indent=2))
