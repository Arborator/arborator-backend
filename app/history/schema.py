from marshmallow import fields, Schema

class GrewHistorySchema(Schema):
    """HIstory schema used to communicated with the frontend"""
    id = fields.Integer(attribute="id")
    uuid = fields.String(attribute="uuid")
    request = fields.String(attribute="request")
    type = fields.String(attribute="type")
    favorite = fields.Boolean(attribute="favorite")
    date = fields.Integer(attribute="date")
    modifiedSentences = fields.Integer(attribute="modified_sentences")