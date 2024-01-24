from marshmallow import fields, Schema

class GrewHistorySchema(Schema):
     
    id = fields.Integer(attribute="id")
    name = fields.String(attribute="name")
    request = fields.String(attribute="request")
    type = fields.Integer(attribute="type")
    favorite = fields.Boolean(attribute="favorite")
    date = fields.Integer(attribute="date")
    modifiedSentences = fields.Integer(attribute="modified_sentences")