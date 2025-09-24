import datetime
import hashlib
import hmac
import json
import time
from urllib.parse import urlparse
from logging import getLogger

import requests

from translate.api_abs import TranslateApiAbs, TextResp

logger = getLogger("translate.api.tencent")


def tencent_request(
        s_key: tuple[str, str],
        method: str,
        url: str,
        service: str,
        action: str,
        region: str = "",
        query: dict = None,
        headers: dict = None,
        body: dict = None,
        version: str = None,
        token: str = "",
        verify=True
) -> requests.Response:
    """附带签名的请求"""

    def sign(key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    urlp = urlparse(url)
    secret_id, secret_key = s_key
    method = method.upper()
    headers = dict() if headers is None else headers
    headers["content-type"] = (
        "application/json; charset=utf-8"
        if method == "POST"
        else "application/x-www-form-urlencoded"
    )
    headers["x-tc-action"] = action
    headers["host"] = urlp.hostname
    payload = json.dumps(body, ensure_ascii=False)
    algorithm = "TC3-HMAC-SHA256"
    timestamp = int(time.time())
    date = datetime.datetime.fromtimestamp(
        timestamp, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%d")
    headers_items = [(k.lower(), headers[k].lower()) for k in sorted(headers)]
    signed_headers = ";".join(sorted(headers)).lower()
    canonical_query_string = "&".join(
        [urlp.query, *[f"{k}={v}" for k, v in (query or {}).items()]]
    )
    canonical_request = (
        f"{method}\n"
        f"{urlp.path or '/'}\n"
        f"{canonical_query_string}\n"  # query
        f"{'\n'.join([':'.join([k.lower(), v.lower()]) for k, v in headers_items])}\n\n"  # headers
        f"{signed_headers}\n"  # need sign keys
        f"{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"  # signed body
    )
    logger.debug(f">>> canonical_request: \n{canonical_request}\n")
    credential_scope = date + "/" + service + "/" + "tc3_request"
    hashed_canonical_request = hashlib.sha256(
        canonical_request.encode("utf-8")
    ).hexdigest()
    string_to_sign = (
        f"{algorithm}\n"
        f"{str(timestamp)}\n"
        f"{credential_scope}\n"
        f"{hashed_canonical_request}"
    )
    logger.debug(f">>> string_to_sign: \n{string_to_sign}\n")
    secret_date = sign(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = sign(secret_date, service)
    secret_signing = sign(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    logger.debug(f">>> signature: \n{signature}\n" )
    headers["Authorization"] = (
        f"{algorithm} "
        f"Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers["X-TC-Timestamp"] = str(timestamp)
    headers["X-TC-Version"] = str(version)
    if region:
        headers["X-TC-Region"] = region
    if token:
        headers["X-TC-Token"] = token
    return requests.request(
        method,
        url,
        headers=headers,
        data=payload,
        verify=verify,
    )


class TranslateApiTencent(TranslateApiAbs):
    lang_map = {
        "zh": "zh",
        "en": 'en',
        "tw": "zh-TW",
    }

    def ocr(self, image: bytes):
        """OCR"""

    def translate_text(self, text: str, to_lang: str, from_lang: str) -> TextResp:
        resp = tencent_request(
            s_key=self.auth,
            method="POST",
            url="https://tmt.tencentcloudapi.com",
            service="tmt",
            action="TextTranslate",
            version="2018-03-21",
            region="ap-guangzhou",
            body={
                "SourceText": text,
                "Source": from_lang or "auto",
                "Target": to_lang,
                "ProjectId": 0,
                # "UntranslatedText": "",
                # "TermRepoIDList": [
                #     None
                # ],
                # "SentRepoIDList": [
                #     None
                # ]
            }
        )

        logger.debug("Resp: %s", resp.text)
        if resp.status_code != 200:
            logger.error("HTTP_CODE Error [%d] %s", resp.status_code, resp.text)
            raise

        resp = resp.json()
        if resp["Response"].get("UsedAmount") is None:
            logger.error("翻译失败, resp: %s", resp)
            raise

        self.meta.usage.text += resp["Response"]["UsedAmount"]
        return TextResp(
            src=text,
            dst=resp.get("Response").get("TargetText"),
        )

    def translate_image(self, image: bytes, target_lang: str, from_lang: str) -> str:
        pass

    def translate_document(self, document: bytes, target_lang: str,
                           from_lang: str) -> str:
        pass

    def usage(self) -> str:
        pass
