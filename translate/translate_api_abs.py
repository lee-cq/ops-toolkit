
import abc

class TranslateApiAbs(abc.ABC):


    @abc.abstractmethod
    def translate_text(self, text: str, target_lang: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def translate_image(self, image: bytes, target_lang: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def translate_document(self, document: bytes, target_lang: str) -> str:
        raise NotImplementedError

    
    @abc.abstractmethod
    def usage(self) -> str:
        raise NotImplementedError