import os
from typing import List, Type

from cryptography.hazmat.primitives.serialization import load_pem_private_key

basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = "app/tmp/data/"
UPLOAD_IMAGE_FOLDER = "app/uploads/images"
MAX_TOKENS = 200000

if not os.path.isdir(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

class Config:
    CONFIG_NAME = "base"
    USE_MOCK_EQUIVALENCY = False
    DEBUG = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SECRET_KEY = 'p9Bv<3Eid9%$i01jge87rt32trig87'
    basedir = os.path.dirname(os.path.abspath(__file__))
    FIRSTADMINKEY="azer"
    UPLOAD_FOLDER = UPLOAD_FOLDER
    SESSION_COOKIE_HTTPONLY = False
    SESSION_COOKIE_SECURE = True
    MAX_TOKENS = MAX_TOKENS

class DevelopmentConfig(Config):
    CONFIG_NAME = "dev"
    SECRET_KEY = os.getenv(
        "DEV_SECRET_KEY", "You can't see California without Marlon Widgeto's eyes"
    )
    DEBUG = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///{0}/app-dev.db".format(basedir)

    DEBUG = True
    SQLALCHEMY_ECHO = False # changed it because the log was too long
    basedir = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
            'sqlite:///' + os.path.join(basedir, 'arborator_dev.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    ENV = 'dev'
    fname = 'keys/arborator-grew-dev.pem'
    APP_ID = open('keys/arborator-grew-dev-appid.txt').read()
    cert_bytes = open(fname, 'rb').read()
    PKEY = load_pem_private_key(cert_bytes, None)

    PROJECT_IMAGE_FOLDER = UPLOAD_IMAGE_FOLDER
    UPLOAD_IMAGE_EXTENSIONS = ['.jpg', '.png', '.gif', '.jpeg']


class TestingConfig(Config):
    CONFIG_NAME = "test"
    SECRET_KEY = os.getenv("TEST_SECRET_KEY", "Thanos did nothing wrong")
    DEBUG = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///{0}/app-test.db".format(basedir)
    
    DEBUG = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    basedir = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'arborator_test.sqlite')

    PROJECT_IMAGE_FOLDER = UPLOAD_IMAGE_FOLDER
    UPLOAD_IMAGE_EXTENSIONS = ['.jpg', '.png', '.gif', '.jpeg']


class ProductionConfig(Config):
    CONFIG_NAME = "prod"
    SECRET_KEY = os.getenv("PROD_SECRET_KEY", "I'm Ron Burgundy?")
    DEBUG = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///{0}/app-prod.db".format(basedir)

    DEBUG = False
    basedir = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
            'sqlite:///' + os.path.join(basedir, 'arborator_prod.sqlite')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    ENV = 'prod'
    fname = 'keys/arborator-grew.pem'
    APP_ID = open('keys/arborator-grew-appid.txt').read()
    cert_bytes = open(fname, 'rb').read()
    PKEY = load_pem_private_key(cert_bytes, None)

    PROJECT_IMAGE_FOLDER = UPLOAD_IMAGE_FOLDER
    UPLOAD_IMAGE_EXTENSIONS = ['.jpg', '.png', '.gif', '.jpeg']


EXPORT_CONFIGS: List[Type[Config]] = [
    DevelopmentConfig,
    TestingConfig,
    ProductionConfig,
]
config_by_name = {cfg.CONFIG_NAME: cfg for cfg in EXPORT_CONFIGS}
