from marshmallow import fields, Schema


class UserSchema(Schema):
    """User schema"""

    id = fields.String(attribute="id")
    auth_provider = fields.String(attribute="auth_provider")
    username = fields.String(attribute="username")
    first_name = fields.String(attribute="first_name")
    family_name = fields.String(attribute="family_name")
    picture_url = fields.String(attribute="picture_url")
    super_admin = fields.Boolean(attribute="super_admin")
    created_date = fields.DateTime(attribute="created_date")
    last_seen = fields.DateTime(attribute="last_seen")