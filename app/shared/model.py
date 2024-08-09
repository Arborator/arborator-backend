import base64

class BaseM(object):
    def as_json(self, exclude=[], include={}):
        json_rep = dict()
        for k in vars(self):
            if k in exclude:
                continue
            elif k[0] == "_":
                continue
            elif type(getattr(self, k)) is bytes:
                json_rep[k] = str(base64.b64encode(getattr(self, k)))
            else:
                json_rep[k] = getattr(self, k)
        for k in include:
            json_rep[k] = include[k]
        return json_rep
