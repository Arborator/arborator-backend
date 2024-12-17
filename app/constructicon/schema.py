from marshmallow import fields, Schema


class ConstructiconSchema(Schema):
    """Constructicon schema shared with the db"""
    id = fields.String(attribute="id")
    title = fields.String(attribute="title")
    description = fields.String(attribute="description")
    grewQuery = fields.String(attribute="grew_query")
    tags = fields.List(fields.String(), attribute="tags")
