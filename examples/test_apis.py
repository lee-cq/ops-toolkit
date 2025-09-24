import os

os.environ["TRANSLATE_CONFIG_PATH"] = "_lo_config.toml"

from translate.config import config

def test_api():
    for api in config.apis:
        api.api.translate_text("我爱你", "en", "zh")
