import os
from pathlib import Path

from mongoengine import connect
import yaml

class BaseConfig:
    MONGODB_SETTINGS = {
        'db': 'wikiloult_dev',
        'host': '127.0.0.1',
        'port': 27017}
    SALT = "loultgamennww"
    AUDIO_RENDER_FOLDER = Path(__file__).absolute().parent.parent / Path("static/sound/")


class DebugConfig(BaseConfig):
    """Debug Flask Config """

    # Db Settings
    MONGODB_SETTINGS = {
        'db': 'wikiloult_dev',
        'host': '127.0.0.1',
        'port': 27017}

    # Flask settings
    SECRET_KEY = 'Wikiloultennww'
    DEBUG = True


class ProductionConfig(BaseConfig):
    # Flask settings
    SECRET_KEY = 'Wpse'
    DEBUG = False

    # Db Settings
    MONGODB_SETTINGS = {
        'db': 'wikiloult',
        'host': '127.0.0.1',
        'port': 27017}


config_mapping = {
    "prod": ProductionConfig,
    "dev": DebugConfig
}


def get_config(flask_config=None):
    """Returns the right config. If not argument is passed, loads the config
     depending on the set FLASK_CONFIG environment variable.
    Falls back to ProductionConfig if none is found"""
    # the "passed argument" way supercedes everything.
    if flask_config is None:
        # loading optional dotenv file. It won't override any existing env variables
        config_filepath = Path(__file__).absolute().parent.parent / Path("config.yml")
        if config_filepath.is_file():
            with open(config_filepath) as yml_file:
                config_dict = yaml.safe_load(yml_file)
        else:
            config_dict = None
        if "FLASK_CONFIG" in config_dict:
            flask_config = config_dict["FLASK_CONFIG"]
    config_cls = config_mapping.get(flask_config, ProductionConfig)

    # if the config is for regular production, overloading default attributes
    # based on the env variables or the .env file variables
    if config_dict is not None:
        attributes = [att for att in dir(config_cls) if not att.startswith("__")]
        for attr in attributes:
            if attr in config_dict:
                setattr(config_cls, attr, config_dict[attr])

    return config_cls


def set_up_db(config: BaseConfig):
    """Setting up the database based on a config object"""
    connect(config.MONGODB_SETTINGS["db"],
            host=config.MONGODB_SETTINGS["host"],
            port=config.MONGODB_SETTINGS["port"])