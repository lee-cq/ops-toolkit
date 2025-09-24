"""
配置文件处理

1. 公开配置
2. API秘钥
"""
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from translate.api_abs import TranslateApiAbs


class UsageModel(BaseModel):
    text: int = 0
    image: int = 0


class KeyModel(BaseModel):
    api_type: str
    text: int = 0
    image: int = 0
    auth: tuple[str, str]
    usage: UsageModel = UsageModel()

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


class Config(BaseModel):
    apis: list[KeyModel] = []
    app_name: str = "translate"
    data_dir: Path = Path.cwd() / f".{app_name.lower()}"
    translation_history_path: Path = data_dir / "translation_history.db"
    log_path: Path = data_dir / f"{app_name.lower()}.log"
    hotkey: str = '<ctrl>+<alt>+d'
    config_path: Path

    def save(self):
        raise NotImplementedError()

    def model_post_init(self, context: Any, /) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

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
    for filename in [".translate_config.toml", ".translate_config.json"]:
        config_path = home_dir / filename
        if config_path.exists():
            return config_path

    # 3. 检查当前目录下的 translate_config 文件
    current_dir = Path.cwd()
    for filename in ["translate_config.toml", "translate_config.json", "_lo_config.toml", "_lo_config.json"]:
        config_path = current_dir / filename
        if config_path.exists():
            return config_path

    # 5. 在当前目录下创建默认配置文件 (使用toml格式)
    default_config = current_dir / "translate_config.toml"
    default_config.touch()
    return default_config


def load_config(path: str = "") -> Config:
    if not path:
        path = find_config_path()

    p = Path(path)
    if not p.exists():
        return Config()
    if p.suffix == '.json':
        from json import load
        val = load(p.open("rb"))
        val['config_path'] = p
        return Config.model_validate(val)
    if p.suffix == ".toml":
        from tomllib import load
        val = load(p.open("rb"))
        val['config_path'] = p
        return Config.model_validate(val)
    raise ValueError(f"config file format error, {p=}")


config = load_config()
