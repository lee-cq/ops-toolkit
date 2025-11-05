import hashlib
import random
from urllib.parse import urlencode

from logging import getLogger
import requests

from translate.api_abs import TranslateApiAbs, TextResp

logger = getLogger("translate.api.baidu")


class TranslateApiBaidu(TranslateApiAbs):
    lang_map = {
        "zh": "zh",
        "en": 'en',
        "tw": "cht",
    }

    def translate_image(self, image: bytes, target_lang: str, from_lang: str) -> str:
        pass

    def translate_document(self, document: bytes, target_lang: str,
                           from_lang: str) -> str:
        pass

    def usage(self) -> str:
        pass

    def translate_text(self, text, to_lang, from_lang, ) -> TextResp:
        url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        salt = random.randint(32768, 65536)
        appid, appkey = self.auth
        sign = hashlib.md5(
            (appid + text + str(salt) + appkey).encode("utf-8")
        ).hexdigest()
        body = urlencode({
            "appid": appid,
            "q":     text,
            "from":  from_lang,
            "to":    to_lang,
            "salt":  salt,
            "sign":  sign,
        })
        resp = requests.post(
            url=url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=body,
        )
        self.debugger(resp, body)

        if resp.status_code != 200:
            logger.error("HTTP Code not 200 [%s] %s", resp.status_code, resp.text)
            raise Exception(resp.text)

        if not resp.json().get("trans_result"):
            logger.error("Can not get trans result. [%s] %s", resp.status_code, resp.text)
            raise Exception(resp.text)

        rst = resp.json().get("trans_result")
        "\n".join([_.get("dst") for _ in rst])

        return TextResp(
            src="\n".join([_.get("src") for _ in rst]),
            dst="\n".join([_.get("dst") for _ in rst]),
        )
