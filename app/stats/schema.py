from marshmallow import Schema, fields


class TopUserSchema(Schema):
    username = fields.String(attribute="username")
    treesNumber = fields.Integer(attribute="trees_number")
    userAvatar = fields.String(attribute="user_avatar")
    
class LastReadAccessSchema(Schema):
    lastRead = fields.Integer(attribute="last_read")
    lastReadUsername = fields.String(attribute="last_read_username")
    
class LastWriteAccessSchema(Schema):
    lastWrite = fields.Integer(attribute="last_write")
    lastWriteUsername = fields.String(attribute="last_write_username")

class StatProjectSchema(Schema):
    users = fields.List(fields.String, attribute="users")
    samplesNumber = fields.Integer(attribute="samples_number")
    treesNumber = fields.Integer(attribute="trees_number")
    sentencesNumber = fields.Integer(attribute="sentences_number")
    tokensNumber = fields.Integer(attribute="tokens_number")
    topUser = fields.Nested(TopUserSchema, attribute="top_user")
    lastRead = fields.Nested(LastReadAccessSchema, attribute="last_read")
    lastWrite = fields.Nested(LastWriteAccessSchema, attribute="last_write")