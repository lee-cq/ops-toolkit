"""

"""
import json
import os
from typing import Optional
import urllib.request
import urllib.parse

import ssl as ssllib

from utils import logger


def request(method, url, headers=None, body=None, ssl=False, timeout=5):
    """
    内置urllib实现通用HTTP请求
    :param method: 请求方法 GET/POST/PUT/DELETE
    :param url: 请求地址
    :param headers: 请求头字典
    :param body: 请求体，str/bytes，json字符串/表单字符串均可
    :param ssl: True=不校验SSL证书（开发自测用），False=严格校验证书
    :param timeout: 超时秒数
    :return: Response 对象
    """
    # 处理body字节化
    req_body: Optional[bytes] = None
    if body is not None:
        if isinstance(body, str):
            req_body = body.encode("utf-8")
        else:
            req_body = body

    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", "Python/urllib/mail Checker(0.1)")

    # 构建请求对象
    req = urllib.request.Request(
        url=url,
        data=req_body,
        headers=headers,
        method=method.upper()
    )

    # SSL上下文控制：关闭证书校验（自测专用）
    ctx = None
    if ssl:
        ctx = ssllib.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssllib.CERT_NONE

    # 发起请求
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp


def send_teams_card(
        hook_url: str,
        msg
) -> bool:
    body = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": msg
                        }
                    ]
                }
            }
        ]
    }
    try:
        return request(
            "POST",
            hook_url,
            body=json.dumps(body),
            headers={"Content-Type": "application/json"},
            ssl=False,
        )
    except Exception as err:
        logger.error(err)
        return False


def send_teams_notify_env(msg) -> bool:
    return send_teams_card(os.getenv("TEAMS_WEBHOOK_URL", ""), msg)

def send_teams_message(hook_url: str, title: str, msg: str) -> bool:
    try:
        return request(
            "POST",
            hook_url,
            body=json.dumps({
                "title": title,
                "msg": msg
            }, ensure_ascii=False),
            headers={"Content-Type": "application/json"},
            ssl=False,
        )
    except Exception as err:
        logger.error(err)
        return False


if __name__ == '__main__':
    pass
