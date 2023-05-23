BASE_ROUTE = "parser"


def register_routes(api, app, root="api"):
    from .controller import api as parser_api

    api.add_namespace(parser_api, path=f"/{root}/{BASE_ROUTE}")