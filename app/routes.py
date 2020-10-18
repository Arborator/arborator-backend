def register_routes(api, app, root="api"):
    from app.user import register_routes as attach_user
    from app.project import register_routes as attach_project

    from app.widget import register_routes as attach_widget

    # Add routes
    attach_user(api, app)
    attach_project(api, app)
    attach_widget(api, app)
