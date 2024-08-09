def register_routes(api, app, root="api"):
    from app.user import register_routes as attach_user
    from app.projects import register_routes as attach_projects
    from app.samples import register_routes as attach_samples
    from app.trees import register_routes as attach_trees
    from app.tags import register_routes as attach_tags
    from app.lexicon import register_routes as attach_lexicon
    from app.constructicon import register_routes as attach_constructicon
    from app.grew import register_routes as attach_grew
    from app.history import register_routes as attach_history
    from app.github import register_routes as attach_github
    from app.klang import register_routes as attach_klang
    from app.parser import register_routes as attach_parser
    from app.stats import register_routes as attach_stats

    # Add routes
    attach_user(api, app, root)
    attach_projects(api, app, root)
    attach_samples(api, app, root)
    attach_trees(api, app, root)
    attach_tags(api, app, root)
    attach_lexicon(api, app, root)
    attach_constructicon(api, app, root)
    attach_grew(api, app, root)
    attach_history(api, app, root)
    attach_github(api, app, root)
    attach_klang(api, app, root)
    attach_parser(api, app, root)
    attach_stats(api, app, root)
