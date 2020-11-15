import os
from flask_script import Manager

from app import create_app, db
from commands.seed_command import SeedCommand


from dotenv import load_dotenv
load_dotenv(dotenv_path=".flaskenv", verbose=True)
from sqlalchemy import MetaData, Table, Column, Integer, String

env = os.getenv("FLASK_ENV") or "test"
print(f"Active environment: * {env} *")
app = create_app(env)

manager = Manager(app)
app.app_context().push()
manager.add_command("seed_db", SeedCommand)


@manager.command
def run():
    app.run()


@manager.command
def init_db():
    print("Creating all resources.")
    db.create_all()


@manager.command
def drop_all():
    if input("Are you sure you want to drop all tables? (y/N)\n").lower() == "y":
        print("Dropping tables...")
        db.drop_all()


@manager.option('--username', help='username of the super_admin to be added')
def add_super_admin(username):
    from app.user.service import UserService
    user = UserService.get_by_username(username=username)
    UserService.change_super_admin(user, True)

    
@manager.option('--username', help='username of the super_admin to be removed')
def remove_super_admin(username):
    from app.user.service import UserService
    user = UserService.get_by_username(username=username)
    UserService.change_super_admin(user, False)


if __name__ == "__main__":
    manager.run()
