from ..models.models import *
try: from ...config import Config # dev
except: from config import Config # prod
from ..utils.conll3 import conll3
from ..repository import user_dao

def get_by_id(user_id: str):
    return user_dao.find_by_id(user_id)

def get_by_username(user_name):
    return user_dao.find_by_name(user_name)
