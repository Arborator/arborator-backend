from marshmallow import fields, Schema

class ProjectSchema(Schema):
    """Project schema"""

    id = fields.Integer(attribute="id")
    projectName = fields.String(attribute="project_name")
    description = fields.String(attribute="description")
    image = fields.String(attribute="image")
    visibility = fields.Integer(attribute="visibility")
    blindAnnotationMode = fields.Boolean(attribute="blind_annotation_mode")
    freezed = fields.Boolean(attribute="freezed")
    config = fields.String(attribute="config")
    language = fields.String(attribute="language")
    diffMode = fields.Boolean(attribute="diff_mode")
    diffUserId = fields.String(attribute="diff_user_id")


class ProjectExtendedSchema(ProjectSchema):
    """Project schema to send to the frontend"""

    users = fields.List(fields.String())
    admins = fields.List(fields.String())
    validators = fields.List(fields.String())
    annotators = fields.List(fields.String())
    guests = fields.List(fields.String())
    numberSentences = fields.Integer(attribute='number_sentences')
    numberSamples = fields.Integer(attribute='number_samples')
    numberTrees = fields.Integer(attribute='number_trees')
    numberTokens = fields.Integer(attribute='number_tokens')
    lastAccess = fields.Integer(attribute='last_access') # this contains the seconds since last access
    lastWriteAccess = fields.Integer(attribute='last_write_access') # this contains the seconds since last write access


class ProjectFeaturesAndMetaSchema(Schema):
    """ProjectFeaturesAndMeta schema"""

    shownFeatures = fields.List(fields.String(), attribute="shown_features")
    shownMeta = fields.List(fields.String(), attribute="shown_meta")
