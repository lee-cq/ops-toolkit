import abc

from pydantic import BaseModel


class TextResp(BaseModel):
    src: str
    dst: str


class ImgResp(BaseModel):
    """"""


class DocumentResp(BaseModel):
    """"""


class OcrResp(BaseModel):
    """"""


class TranslateApiAbs(abc.ABC):
    lang_map = {
        "zh": "zh",
        "en": 'en',
        "tw": "tw",
    }

    def __init__(self, auth):
        self.auth = auth

    def get_lang(self, lang) -> str:
        """重写lan_map

        :param lang:
        :return:
        """
        return self.lang_map[lang]

    @abc.abstractmethod
    def translate_text(self, text: str, to_lang: str, from_lang: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def translate_image(self, image: bytes, target_lang: str, from_lang: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def translate_document(self, document: bytes, target_lang: str,
                           from_lang: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def usage(self) -> str:
        raise NotImplementedError
