BASE_ROUTE = "projects"


def register_routes(api, app, root="api"):
    from .controller import api as project_api
    from .controllerV2 import api as project_apiV2

    api.add_namespace(project_api, path=f"/{root}/{BASE_ROUTE}")
    api.add_namespace(project_apiV2, path=f"/{root}/{BASE_ROUTE}/V2")