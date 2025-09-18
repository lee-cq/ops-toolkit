import os

os.environ["TRANSLATE_CONFIG_PATH"] = "_lo_config.json"

from translate.config import config

print(config.apis[0]._api.translate_text("我啊", "en", "zh"))
