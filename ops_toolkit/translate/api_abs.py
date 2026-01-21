import abc
import logging
import typing

from pydantic import BaseModel

if typing.TYPE_CHECKING:
    from ops_toolkit.config import TranslateApiModel
    from requests import Response

row_request_logger = logging.getLogger("ops_toolkit.row_request")


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

    @staticmethod
    def debugger(response: "Response", req_body: str) -> None:
        row_request_logger.info(
            f"=============== ROW Request ==============\n"
            f"{response.request.method} {response.request.url}\n"
            f"{'\n'.join(f'{k}: {v}' for k, v in response.request.headers.items())}\n\n"
            f"{req_body}\n"
            f"-------------- Response ---------------\n"
            f"HTTP/{response.raw.version / 10.0} {response.status_code} {response.reason}\n"
            f"{'\n'.join(f'{k}: {v}' for k, v in response.headers.items())}\n\n"
            f"{response.json()}\n"
            f"============ Row Request End =============="
        )

    @abc.abstractmethod
    def translate_text(self, text: str, to_lang: str, from_lang: str) -> TextResp:
        raise NotImplementedError

    @abc.abstractmethod
    def translate_image(self, image: bytes, target_lang: str, from_lang: str) -> ImgResp:
        raise NotImplementedError

    @abc.abstractmethod
    def translate_document(
            self,
            document: bytes,
            target_lang: str,
            from_lang: str
    ) -> DocumentResp:
        raise NotImplementedError

    @abc.abstractmethod
    def usage(self) -> str:
        raise NotImplementedError
