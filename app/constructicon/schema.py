from marshmallow import fields, Schema


class ConstructiconSchema(Schema):
    id = fields.String(attribute="id")
    title = fields.String(attribute="title")
    description = fields.String(attribute="description")
    grewQuery = fields.String(attribute="grew_query")
    tags = fields.List(fields.String(), attribute="tags")
