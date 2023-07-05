BASE_ROUTE = "constructicon"

def register_routes(api, app, root="api"):
    from .controller import api as constructicon_api

    api.add_namespace(constructicon_api, path=f"/{root}/{BASE_ROUTE}")