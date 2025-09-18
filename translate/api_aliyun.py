from translate.api_abs import TranslateApiAbs


class TranslateApiAliyun(TranslateApiAbs):
    """"""

    def translate_text(self, text: str, to_lang: str, from_lang: str) -> str:
        pass

    def translate_image(self, image: bytes, target_lang: str, from_lang: str) -> str:
        pass

    def translate_document(self, document: bytes, target_lang: str,
                           from_lang: str) -> str:
        pass

    def usage(self) -> str:
        pass
