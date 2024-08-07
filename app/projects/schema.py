from marshmallow import fields, Schema
import base64


class BlobImageField(fields.Field):
    def _validated(self, value):
        if not isinstance(value, bytes):
            raise "Invalid input type."

        if value is None or value == b"":
            raise "Invalid value"
        
    
    def _serialize(self, value : bytes, attr, obj, **kwargs):
        if value is None:
            return None

        if type(value) == str:
            return value
        return str(base64.b64encode(value))


class ProjectSchema(Schema):
    """Project schema"""

    id = fields.Integer(attribute="id")
    projectName = fields.String(attribute="project_name")
    description = fields.String(attribute="description")
    image = BlobImageField(attribute="image")
    visibility = fields.Integer(attribute="visibility")
    blindAnnotationMode = fields.Boolean(attribute="blind_annotation_mode")
    freezed = fields.Boolean(attribute="freezed")
    config = fields.String(attribute="config")
    language = fields.String(attribute="language")
    syncGithub = fields.String(attribute="sync_github") 
    owner = fields.String(attribute="owner")
    contactOwner = fields.String(attribute="contact_owner")


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
    lastWriteAccess = fields.Integer(attribute='last_write_access') # this contains the seconds since last access


# KK TODO : Ths should be unified with  `ProjectSchema`. However, at the moment,
# ... we have still some unwanted mixing in the typing convention in the frontend.
# ... at term, we should have only snake_case in the python backend, only camelCase 
# ... on the JS frontend and the Schema should be the bridge between both.
class ProjectSchemaCamel(Schema):
    projectId = fields.Integer(attribute="id")
    projectName = fields.String(attribute="project_name")
    description = fields.String(attribute="description")
    image = BlobImageField(attribute="image")
    visibility = fields.Integer(attribute="visibility")
    blindAnnotationMode = fields.Boolean(attribute="blind_annotation_mode")
    freezed = fields.Boolean(attribute="freezed")
    config = fields.String(attribute="config")
    language = fields.String(attribute="language")
    diffMode = fields.Boolean(attribute="diff_mode")
    diffUserId = fields.String(attribute="diff_user_id")


class ProjectFeaturesAndMetaSchema(Schema):
    """ProjectFeaturesAndMeta schema"""

    shownFeatures = fields.List(fields.String(), attribute="shown_features")
    shownMeta = fields.List(fields.String(), attribute="shown_meta")
