from marshmallow import fields, Schema

class SampleSchema(Schema):
    """sample information to be send to the frontend"""
    sampleName = fields.String(attribute="sample_name")
    sentences = fields.Integer(attribute="sentences")
    numberTrees = fields.Integer(attribute="number_trees")
    tokens = fields.Integer(attribute="tokens")
    treesFrom = fields.List(fields.String(), attribute="trees_from")
    treeByUser = fields.Dict(keys=fields.String(), values=fields.Integer(), attribute="tree_by_user")
    tags = fields.Dict(keys=fields.String(), values=fields.Integer(), attribute="tags")
    blindAnnotationLevel = fields.Integer(attribute="blind_annotation_level")