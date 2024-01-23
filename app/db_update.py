import os
from sqlalchemy import create_engine
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("mode", help="prod or dev")
parser.add_argument("version", help="which commits to migrate")
args = parser.parse_args()

if args.mode != 'prod' and args.mode != 'dev':
    print('mode must be prod or dev')
    exit()

if args.version != 'add_grew_history':
    print('version must be add_grew_history')
    exit()

mode = args.mode
basedir = os.path.dirname(os.path.abspath(__file__))
db_path = 'sqlite:///' + os.path.join(basedir, 'arborator_{}.sqlite'.format(mode))

engine = create_engine(db_path)

def migrate_add_grew_history(engine):
    with engine.connect() as connection:
        connection.execute("CREATE TABLE history (id INTEGER NOT NULL, project_id INTEGER, user_id	VARCHAR(256), name VARCHAR(256), request TEXT, type INTEGER, favorite BOOLEAN, date FLOAT, modified_sentence INTEGER, PRIMARY KEY(id), FOREIGN KEY(project_id) REFERENCES projects(id), FOREIGN KEY(user_id) REFERENCES users(id))")


if args.version == 'add_grew_history':
    migrate_add_grew_history(engine)