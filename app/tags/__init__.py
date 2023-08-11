BASE_ROUTE = "projects" 


def register_routes(api, app, root="api"):
    from .controller import api as tags_api

    api.add_namespace(tags_api, path=f"/{root}/{BASE_ROUTE}")