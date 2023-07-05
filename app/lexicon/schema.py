from marshmallow import fields
from marshmallow.schema import Schema


class LexiconItemSchema(Schema):
    """User schema"""

    form = fields.String(attribute="form")
    pos = fields.String(attribute="pos")
    lemma = fields.String(attribute="lemma")
    gloss = fields.String(attribute="gloss")
    frequency = fields.Integer(attribute="frequency")
    features = fields.Dict(attribute="features")
