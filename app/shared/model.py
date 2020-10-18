import base64
import json

from sqlalchemy.ext.declarative import DeclarativeMeta


class BaseM(object):
    def as_json(self, exclude=[], include={}):
        json_rep = dict()
        for k in vars(self):
            # print(getattr(self, k))
            if k in exclude:
                # print(k)
                continue
            elif k[0] == "_":
                continue
            elif type(getattr(self, k)) is bytes:
                # print('yay')
                # print(getattr(self, k))
                json_rep[k] = str(base64.b64encode(getattr(self, k)))
                # json_rep[k] = str(getattr(self, k))
            else:
                json_rep[k] = getattr(self, k)
        for k in include:
            json_rep[k] = include[k]
        return json_rep


# TODO : can remove this class
class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [
                x for x in dir(obj) if not x.startswith("_") and x != "metadata"
            ]:
                data = obj.__getattribute__(field)
                try:
                    # this will fail on non-encodable values, like other classes
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)