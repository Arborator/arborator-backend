from marshmallow import fields, Schema


class BytesField(fields.Field):
    def _validate(self, value):
        if not isinstance(value, bytes):
            raise "Invalid input type."

        if value is None or value == b"":
            raise "Invalid value"


class ProjectSchema(Schema):
    """User schema"""

    id = fields.Integer(attribute="id")
    project_name = fields.String(attribute="project_name")
    description = fields.String(attribute="description")
    image = BytesField(attribute="image")
    visibility = fields.Integer(attribute="visibility")
    show_all_trees = fields.Boolean(attribute="show_all_trees")
    exercise_mode = fields.Boolean(attribute="exercise_mode")
    # default_user_trees = fields.String(attribute="default_user_trees")


class ProjectExtendedSchema(ProjectSchema):
    """User schema to send to the frondend"""

    admins = fields.List(fields.String())
    guests = fields.List(fields.String())
    number_sentences = fields.Integer()
    number_samples = fields.Integer()
    number_trees = fields.Integer()
    number_tokens = fields.Integer()


# KK TODO : Ths should be unified with  `ProjectSchema`. However, at the moment,
# ... we have still some unwanted mixing in the typing convention in the frontend.
# ... at term, we should have only snake_case in the python backend, only camelCase 
# ... on the JS frontend and the Schema should be the bridge between both.
class ProjectSchemaCamel(Schema):
    projectId = fields.Integer(attribute="id")
    projectName = fields.String(attribute="project_name")
    description = fields.String(attribute="description")
    image = BytesField(attribute="image")
    visibility = fields.Integer(attribute="visibility")
    showAllTrees = fields.Boolean(attribute="show_all_trees")
    exerciseMode = fields.Boolean(attribute="exercise_mode")
