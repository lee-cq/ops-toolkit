import abc


class TranslateApiAbs(abc.ABC):

    def __init__(self, auth):
        self.auth = auth

    @abc.abstractmethod
    def translate_text(self, text: str, to_lang: str, from_lang: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def translate_image(self, image: bytes, target_lang: str, from_lang: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def translate_document(self, document: bytes, target_lang: str, from_lang: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def usage(self) -> str:
        raise NotImplementedError
