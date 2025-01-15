from marshmallow import fields, Schema


class UserSchema(Schema):
    """User schema user object serialization"""

    id = fields.String(attribute="id")
    authProvider = fields.String(attribute="auth_provider")
    githubAccessToken = fields.String(attribute="github_access_token")
    username = fields.String(attribute="username")
    firstName = fields.String(attribute="first_name")
    familyName = fields.String(attribute="family_name")
    email = fields.String(attribute="email")
    notShareEmail = fields.Boolean(attribute="not_share_email")
    receiveNewsletter = fields.Boolean(attribute="receive_newsletter")
    pictureUrl = fields.String(attribute="picture_url")
    superAdmin = fields.Boolean(attribute="super_admin")
    createdDate = fields.DateTime(attribute="created_date")
    lastSeen = fields.DateTime(attribute="last_seen")
    canToggleSuperAdmin = fields.Boolean(attribute="can_toggle_super_admin")