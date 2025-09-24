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


def load_config(path: str = "") -> Config:
    if not path:
        from os import getenv
        path = getenv("TRANSLATE_CONFIG_PATH")
        if not path:
            raise ValueError(f"path is empty, {path=}")

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
