# from flask import  redirect, url_for, abort, 
# from flask_login import  current_user
# from functools import wraps
# # from flask_cors import cross_origin

# from app.projects.service import ProjectAccessService, ProjectService

# from ...services import project_service, user_service, robot_service, github_service, samples_service  # type: ignore


# def requires_access_level(access_level):
#     """	decorator for access control. except for superadmins """
#     def decorator(f):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             # not authenticated -> login
#             if not current_user.id:
#                 return redirect(url_for('auth.login'))

#             if kwargs.get("project_name"):
#                 project_id = project_service.get_by_name(
#                     kwargs["project_name"]).id
#             elif kwargs.get("id"):
#                 project_id = kwargs["id"]
#             else:
#                 abort(400)

#             project_access = project_service.get_project_access(
#                 project_id, current_user.id)

#             print("project_access for current user: {}".format(project_access))

#             if not current_user.super_admin:  # super_admin are always admin even if it's not in the table
#                 if project_access < access_level:
#                     abort(403, "User doesn't have the right privileges")
#                 # if isinstance(project_access, int):
#                 #     abort(403, "ERROR isinstance(project_access, int)")
#                 # if project_access is None or project_access.access_level.code < access_level:
#                 #     abort(403, "project_access is None or project_access.access_level.code < access_level")
#                 #  # return redirect(url_for('home.home_page'))

#             return f(*args, **kwargs)
#         return decorated_function
#     return decorator