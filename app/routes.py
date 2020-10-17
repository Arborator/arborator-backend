def register_routes(api, app, root="api"):
    from app.user import register_routes as attach_user

    from app.widget import register_routes as attach_widget

    # Add routes
    attach_user(api, app)
    attach_widget(api, app)
