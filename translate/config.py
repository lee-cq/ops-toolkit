"""
配置文件处理

1. 公开配置
2. API秘钥
"""
from pathlib import Path
from typing import Callable, Any

from pydantic import BaseModel

from translate.translate_api_abs import TranslateApiAbs
from translate.translate_api_baidu import TranslateApiBaidu


def api_factory(api_type: str, auth) -> TranslateApiAbs:
    if api_type == 'baidu':
        return TranslateApiBaidu(auth)
    raise NotImplementedError


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

    def api_factory(self) -> TranslateApiAbs:
        if self.api_type == "baidu":
            return TranslateApiBaidu(self.auth)
        elif self.api_type == "aliyun":
            return TranslateApiBaidu(self.auth)
        raise NotImplementedError


class Config(BaseModel):
    apis: list[KeyModel] = []

    def save(self):
        raise NotImplementedError()


def load_config(path: str = "") -> Config:
    if not path:
        from os import getenv
        path = getenv("TRANSLATE_CONFIG_PATH")
        if not path:
            raise ValueError(f"path is empty, {path=}")

    p = Path(path)
    if not p.exists():
        return Config()
    return Config.model_validate_json(p.read_text())


config = load_config()
