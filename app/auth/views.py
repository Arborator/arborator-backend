from datetime import datetime

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
from flask_login import current_user, login_user, login_required, logout_user
from authomatic.adapters import WerkzeugAdapter
from authomatic import Authomatic


from app.config import Config

from . import auth

from .auth_config import CONFIG

from ..user.service import UserService
from ..user.interface import UserInterface
from ..user.schema import UserSchema
from ..user.model import User
from ..github.service import GithubService 
from ..projects.service import ProjectAccessService


authomatic = Authomatic(CONFIG, Config.SECRET_KEY, report_errors=True)


def parse_user(provider_name, user):
    results_parsed = {}

    if provider_name == "github":
        results_parsed["access_token"] = user.data.get("access_token")
        data = GithubService.get_user_information(results_parsed["access_token"])
        results_parsed["id"] = data.get("id")
        results_parsed["username"] = data.get("login")
        results_parsed["picture_url"] = data.get("avatar_url")
        results_parsed["email"] = data.get("email")

    elif provider_name == "google":
        results_parsed["id"] = user.email
        results_parsed["username"] = user.email.split("@")[0]
        results_parsed["email"] = user.email
        results_parsed["first_name"] = user.first_name
        results_parsed["family_name"] = user.last_name
        results_parsed["picture_url"] = user.picture

    return results_parsed



@auth.route("/login/<provider_name>/")
def login(provider_name) -> Response:
    """
    Login handler.
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
            results_parsed = parse_user(provider_name, result.user)

            # Retrieve the user
            user = UserService.login_by_id(results_parsed.get("id"))

            # If no existing user, create a new one
            if not user:
                username = results_parsed.get("username")
                valid_username = UserService.make_valid_nickname(username)
                unique_username = UserService.make_unique_nickname(valid_username)

                new_attrs: UserInterface = {
                    "id": results_parsed["id"],
                    "auth_provider": result.user.provider.id,
                    "github_access_token": results_parsed.get("access_token"),
                    "username": unique_username,
                    "first_name": results_parsed.get("first_name"),
                    "family_name": results_parsed.get("family_name"),
                    "email": results_parsed.get("email"),
                    "not_share_email": False,
                    "picture_url": results_parsed.get("picture_url"),
                    "super_admin": False,
                    "created_date": datetime.utcnow(),
                    "last_seen": datetime.utcnow(),
                }

                user = UserService.create(new_attrs)
                has_projects = False
            else:
                if  user.auth_provider == "4":
                    changes: UserInterface = {
                        "github_access_token": results_parsed.get("access_token"),
                        "picture_url": results_parsed.get("picture_url"),
                    }
                else: 
                    changes: UserInterface = {
                        "picture_url": results_parsed.get("picture_url")
                    }
                user = UserService.update(user, changes)
                has_projects = ProjectAccessService.user_has_access_to_project(user.id)
            login_user(user, remember=True)
            # If there is no superadmin in DB, add admin privilege to this new user
            if not User.query.filter_by(super_admin=True).first():
                print("firstsuper")
                return make_response(render_template("auth/firstsuper.html"))

            # KK : TODO : It seems that these two following lines are useless because
            # ... this view puspuse is to login (send the cookie) and not to send user
            # ... infos as a json
            user_json = UserSchema().dump(user)
            resp = Response(user_json, status=200, mimetype="application/json")
            if current_app.config["ENV"] == "dev":
                return make_response(
                    render_template("auth/redirect_dev.html", response=resp, has_projects= has_projects)
                )
            elif current_app.config["ENV"] == "prod":
                return make_response(
                    render_template("auth/redirect_prod.html", response=resp, has_projects= has_projects)
                )

    return response


@auth.route("/firstsuper")
@login_required
def firstsuper():
    """
    Handle requests to the /firstsuper route
    """
    return render_template("admin/firstsuper.html")

@auth.route("/checkfirstsuper", methods=["POST"])
@login_required
def checkfirstsuper():
    """
    Handle requests to the /firstsuper route
    """
    mdp = request.form.get("password")
    if mdp == Config.FIRSTADMINKEY:

        user = UserService.get_by_id(current_user.id)
        changes: UserInterface = {"super_admin": True}
        UserService.update(user, changes)
        message = "You are logged in as the first super user"
    else:
        message = "Access as superadmin has been denied."
    flash(message)
    return redirect("https://127.0.0.1:8080")

