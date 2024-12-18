import os
from sqlalchemy import create_engine, text
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("mode", help="prod or dev")
parser.add_argument("version", help="which commits to migrate")
args = parser.parse_args()

if args.mode != 'prod' and args.mode != 'dev':
    print('mode must be prod or dev')
    exit()

if args.version != 'refactor_github' and args.version != 'add_grew_history' and args.version != 'update_dependencies':
    print('version must be refactor_github or add_grew_history')
    exit()

mode = args.mode
basedir = os.path.dirname(os.path.abspath(__file__))
db_path = 'sqlite:///' + os.path.join(basedir, 'arborator_{}.sqlite'.format(mode))

engine = create_engine(db_path)

def migrate_add_grew_history(engine):
    with engine.connect() as connection:
        connection.execute("CREATE TABLE history (id INTEGER NOT NULL, uuid TEXT,  project_id INTEGER, user_id VARCHAR(256), request TEXT, type VARCHAR(256), favorite BOOLEAN, date FLOAT, modified_sentences INTEGER, PRIMARY KEY(id), FOREIGN KEY(project_id) REFERENCES projects(id), FOREIGN KEY(user_id) REFERENCES users(id))")

def migrate_refactor_github(engine):
    with engine.connect() as connection:
        connection.execute("DELETE FROM github_repositories;")
        connection.execute("DELETE FROM commit_status;")

def migrate_update_dependencies(engine):
    with engine.connect() as connection:
        connection.execute(text("ALTER TABLE projects ADD collaborative_mode BOOLEAN NOT NULL DEFAULT(1);"))

if args.version == 'add_grew_history':
    migrate_add_grew_history(engine)
           
if args.version == 'refactor_github':
    migrate_refactor_github(engine)

if args.version == 'update_dependencies':
    migrate_update_dependencies(engine)