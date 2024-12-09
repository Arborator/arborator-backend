from flask import (
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    Response,
)
from flask_login import login_user, login_required
from authomatic.adapters import WerkzeugAdapter
from authomatic import Authomatic


from app.config import Config

from . import auth

from .auth_config import CONFIG

from ..user.service import UserAuthService
from ..user.model import User

from ..projects.service import ProjectAccessService

authomatic = Authomatic(CONFIG, Config.SECRET_KEY, report_errors=True)

@auth.route("/login/<provider_name>/")
def login(provider_name) -> Response:
    """login using social authentication

    Args:
        provider_name (string): github | google

    Returns:
        Response
    """
    # We need response object for the WerkzeugAdapter.
    response = make_response()

    # Log the user in, pass it the adapter and the provider name.
    result = authomatic.login(WerkzeugAdapter(request, response), provider_name)

    # If there is no LoginResult object, the login procedure is still pending.
    if result:
        if result.error:
            print("auth/views.py Error: {}".format(result.error))
            abort(500)

        if result.user:
            if provider_name == "google":
                # specific to google, we need to update the user to get more info.
                result.user.update()
                
            # parse the format specific to each provider
            results_parsed = UserAuthService.parse_user_information(provider_name, result.user)

            user = UserAuthService.create_or_update_user(results_parsed)
            
            has_projects = ProjectAccessService.user_has_access_to_project(user.id)
            login_user(user, remember=True)
            
            # If there is no superadmin in DB, add admin privilege to this new user
            if not User.query.filter_by(super_admin=True).first():
                print("firstsuper")
                return make_response(render_template("auth/firstsuper.html"))

            if current_app.config["ENV"] == "dev":
                return make_response(
                    render_template("auth/redirect_dev.html", has_projects= has_projects)
                )
            elif current_app.config["ENV"] == "prod":
                return make_response(
                    render_template("auth/redirect_prod.html", has_projects= has_projects)
                )
    return response


@auth.route("/firstsuper")
@login_required
def firstsuper():
    """Handle the request for /firstsuper

    Returns:
        template: render the template of the first user 
    """
    return render_template("admin/firstsuper.html")


