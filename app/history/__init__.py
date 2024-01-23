BASE_ROUTE = "projects" 


def register_routes(api, app, root="api"):
    from .controller import api as history_api

    api.add_namespace(history_api, path=f"/{root}/{BASE_ROUTE}")