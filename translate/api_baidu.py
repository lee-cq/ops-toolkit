import hashlib
import random
from urllib.parse import urlencode

import requests

from translate.api_abs import TranslateApiAbs


class TranslateApiBaidu(TranslateApiAbs):

    lang_map = {
        "zh": "zh",
        "en": 'en',
        "tw": "tw",
    }
    def translate_image(self, image: bytes, target_lang: str, from_lang: str) -> str:
        pass

    def translate_document(self, document: bytes, target_lang: str,
                           from_lang: str) -> str:
        pass

    def usage(self) -> str:
        pass

    def translate_text(self, text, to_lang, from_lang, ):
        url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        salt = random.randint(32768, 65536)
        appid, appkey = self.auth
        sign = hashlib.md5(
            (appid + text + str(salt) + appkey).encode("utf-8")).hexdigest()
        resp = requests.post(
            url=url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=urlencode({
                "appid": appid,
                "q": text,
                "from": from_lang,
                "to": to_lang,
                "salt": salt,
                "sign": sign,
            }),
        )
        if resp.status_code != 200:
            raise Exception(resp.text())
        return resp.json().get("trans_result")
