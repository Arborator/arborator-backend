from marshmallow import fields, Schema


class GithubRepositorySchema(Schema):
    id = fields.Integer(attribute="id")
    projectId = fields.Integer(attribute="project_id")
    userId = fields.String(attribute="user_id")
    repositoryName = fields.String(attribute="repository_name")
    branch = fields.String(attribute="branch")
    baseSha = fields.String(attribute="base_sha")