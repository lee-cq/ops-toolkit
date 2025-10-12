import abc
import typing

from pydantic import BaseModel

if typing.TYPE_CHECKING:
    from translate.config import TranslateApiModel


class TextResp(BaseModel):
    src: str
    dst: str


class ImgResp(TextResp):
    """"""


class DocumentResp(TextResp):
    """"""


class OcrResp(TextResp):
    """"""


class TranslateApiAbs(abc.ABC):
    lang_map = {
        "zh": "zh",
        "en": 'en',
        "tw": "tw",
    }

    def __init__(self, auth, meta):
        self.auth = auth
        self.meta: "TranslateApiModel" = meta

    def get_lang(self, lang) -> str:
        """重写lan_map

        :param lang:
        :return:
        """
        return self.lang_map[lang]

    @abc.abstractmethod
    def translate_text(self, text: str, to_lang: str, from_lang: str) -> TextResp:
        raise NotImplementedError

    @abc.abstractmethod
    def translate_image(self, image: bytes, target_lang: str, from_lang: str) -> ImgResp:
        raise NotImplementedError

    @abc.abstractmethod
    def translate_document(self,
                           document: bytes,
                           target_lang: str,
                           from_lang: str
                           ) -> DocumentResp:
        raise NotImplementedError

    @abc.abstractmethod
    def usage(self) -> str:
        raise NotImplementedError
