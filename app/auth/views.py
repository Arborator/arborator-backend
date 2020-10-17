from datetime import datetime
import json
import requests

from flask import abort, current_app, flash, make_response, redirect, render_template, request, Response, session
from flask_login import current_user, login_user, login_required, logout_user

from authomatic.adapters import WerkzeugAdapter
from authomatic import Authomatic


from app import db
from app.config import BaseConfig as Config

from . import auth
from ..user.model import User, load_user, AlchemyEncoder
from .auth_config import CONFIG


authomatic = Authomatic(CONFIG, Config.SECRET_KEY, report_errors=True)


def parse_user(provider_name, user):
    results_parsed = {}

    if provider_name == "github":
        access_token = user.data.get("access_token")
        data = get_username(access_token, "github")
        results_parsed["id"] = data.get("id")
        results_parsed["username"] = data.get("login")
        results_parsed["picture_url"] = data.get("avatar_url")
        results_parsed["email"] = data.get("email")

    elif provider_name == "google":
        results_parsed["id"] = user.email
        results_parsed["username"] = user.email.split('@')[0]
        results_parsed["email"] = user.email
        results_parsed["first_name"] = user.first_name
        results_parsed["family_name"] = user.last_name
        results_parsed["picture_url"] = user.picture

    return results_parsed


def get_username(access_token, provider_name):
    if provider_name == "github":
        headers = {"Authorization": "bearer " + access_token}
        response = requests.get("https://api.github.com/user", headers=headers)
        data = response.json()
        return data
    else:
        abort(404)


# @auth.route('/login/<provider_name>/', methods=['GET', 'POST'])
@auth.route('/login/<provider_name>/')
def login(provider_name):
    """
    Login handler.
    """
    print('KK logging ...', current_app.config)

    # print( current_app.config )
    # We need response object for the WerkzeugAdapter.
    response = make_response()

    # Log the user in, pass it the adapter and the provider name.
    result = authomatic.login(WerkzeugAdapter(
        request, response), provider_name)
    print("KK agter result", result)
    # Sessions!! coming back
    # session=session,
    # session_saver=lambda: app.save_session(session, response))

    # If there is no LoginResult object, the login procedure is still pending.
    if result:
        if result.error:
            print("Error: {}".format(result.error))
            abort(500)

        if result.user:
            if provider_name == "google":
                # specific to google, we need to update the user to get more info.
                result.user.update()
            else:
                pass
            # parse the format specific to each provider
            results_parsed = parse_user(provider_name, result.user)

            # save user id to session
            user = User.query.filter_by(
                id=results_parsed.get("id")).first()
            # session['email'] = result.user.email
            if user is None:

                username = results_parsed.get("username")
                username = User.make_valid_nickname(username)
                username = User.make_unique_nickname(username)

                # Save UserDetails To Db
                user, created = User.get_or_create(
                    db.session,  # TODO TO REMOVE !!!!
                    id=results_parsed["id"],
                    auth_provider=result.user.provider.id,
                    username=results_parsed.get("username"),
                    # email=result.user.email,
                    first_name=results_parsed.get("first_name"),
                    family_name=results_parsed.get("family_name"),
                    picture_url=results_parsed.get("picture_url"),
                    super_admin=False,
                    created_date=datetime.utcnow(),
                    last_seen=datetime.utcnow()
                )

            User.setPictureUrl(db.session, user.username, results_parsed.get(
                "picture_url"))  # always get the lastest picture on login

            login_user(user, remember=True)
            session['logged_in'] = True  # ?????
            print('============', user)

            if not User.query.filter_by(super_admin=True).first():
                print("firstsuper")
                return make_response(render_template('auth/firstsuper.html'))

    # headers = {'Content-Type': 'text/html'}
    # return make_response(render_template('index.html'),200,headers)

            js = json.dumps(user.as_json(), default=str)
            resp = Response(js, status=200,  mimetype='application/json')
            if current_app.config['ENV'] == 'development':
                print("KK FFOOOFOFOO")
                # return redirect("https://localhost:8080/")
                # dev # it seems that response=resp is useless
                return make_response(render_template('auth/redirect_dev.html', response=resp))
            elif current_app.config['ENV'] == 'production':
                # return redirect("https://arboratorgrew.ilpga.fr/")
                # prod
                return make_response(render_template('auth/redirect_prod.html', response=resp))
    print("KK before response")
    return response


# @auth.route('/login/userinfos', methods=['GET', 'POST'])
# def getUserInfos():
#     # print(session)
#     user_id = session.get("user_id")
#     if not user_id:
#         user_id = session.get("_user_id")
#     # print('-----------------',session,user_id)
#     user = load_user(user_id)
#     user.last_seen = datetime.utcnow()
#     db.session.commit()
#     js = json.dumps(user.as_json(), default=str)  # returns empty data !
#     js = json.dumps(user, cls=AlchemyEncoder)
#     resp = Response(js, status=200,  mimetype='application/json')
#     return resp


@auth.route('/firstsuper')
@login_required
def firstsuper():
    """
    Handle requests to the /firstsuper route
    """
    return render_template('admin/firstsuper.html')
    # redirect to the login page
    # return redirect(url_for('auth.choose_provider'))


@auth.route('/logout')
def logout():
    """
    Handle requests to the /logout route
    Log an employee out through the logout link
    """
    logout_user()
    # js = json.dumps({'logout':True}, default=str)
    # resp = Response(js, status=200,  mimetype='application/json')
    return {}


@auth.route('/checkfirstsuper', methods=['POST'])
@login_required
def checkfirstsuper():
    """
    Handle requests to the /firstsuper route
    """
    print("KK Checkfirstsuper")
    mdp = request.form.get('password')
    print("KK mdp", mdp)
    print("KK Config.FIRSTADMINKEY", Config.FIRSTADMINKEY)
    if mdp == Config.FIRSTADMINKEY:

        user = load_user(current_user.id)
        user.super_admin = True
        db.session.commit()
        # print("88888888",user,user.super_admin)
        message = "You are logged in as the first super user"
    else:
        message = "Access as superadmin has been denied."
    flash(message)
    print("KK message", message)
    # redirect to the login page
    # TODO : fix this ugly thing, redirecting to url_for('home.home_page') goes to the bad port
    return redirect("https://127.0.0.1:8080")
    # return redirect("/")
