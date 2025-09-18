import os

os.environ["TRANSLATE_CONFIG_PATH"] = "_lo_config.toml"

from translate.config import config

print(config.apis[0].api.translate_text("我爱你", "en", "zh"))
