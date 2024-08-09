BASE_ROUTE = "projects"


def register_routes(api, app, root="api"):
    from .controller import api as statics_api

    api.add_namespace(statics_api, path=f"/{root}/{BASE_ROUTE}")