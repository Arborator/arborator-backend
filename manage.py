import os
import click
from dotenv import load_dotenv

load_dotenv(dotenv_path=".flaskenv", verbose=True)

from app import create_app, db

env = os.getenv("FLASK_ENV") or "test"
print(f"Active environment: * {env} *")
app = create_app(env)


@click.group()
def cli():
    pass


@cli.command(name="seed_db")
def seed_db_cmd():
    """Drop/create DB and commit."""
    from commands.seed_command import seed_database

    with app.app_context():
        seed_database()


@cli.command(name="run")
def run_cmd():
    app.run()


@cli.command(name="init_db")
def init_db_cmd():
    with app.app_context():
        print("Creating all resources.")
        db.create_all()


@cli.command(name="drop_all")
def drop_all_cmd():
    import click as _click

    with app.app_context():
        if _click.confirm("Are you sure you want to drop all tables?"):
            print("Dropping tables...")
            db.drop_all()
            print("Tables dropped.")


@cli.command(name="add_super_admin")
@click.option('--username', required=True, help='username of the super_admin to be added')
def add_super_admin_cmd(username):
    """Add super admin by username."""
    with app.app_context():
        from app.user.service import UserService
        user = UserService.get_by_username(username=username)
        if not user:
            raise click.ClickException(f"User '{username}' not found")
        UserService.change_super_admin(user, True)
        print(f"User {username} set as super admin.")


@cli.command(name="remove_super_admin")
@click.option('--username', required=True, help='username of the super_admin to be removed')
def remove_super_admin_cmd(username):
    """Remove super admin by username."""
    with app.app_context():
        from app.user.service import UserService
        user = UserService.get_by_username(username=username)
        if not user:
            raise click.ClickException(f"User '{username}' not found")
        UserService.change_super_admin(user, False)
        print(f"User {username} removed from super admin.")


if __name__ == "__main__":
    cli()