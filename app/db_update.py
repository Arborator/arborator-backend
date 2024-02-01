import os
from sqlalchemy import create_engine
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("mode", help="prod or dev")
parser.add_argument("version", help="which commits to migrate (add refecator_github)")
args = parser.parse_args()

if args.mode != 'prod' and args.mode != 'dev':
    print('mode must be prod or dev')
    exit()

if args.version != 'refactor_github':
    print('version must be refactor_github')
    exit()

mode = args.mode
basedir = os.path.dirname(os.path.abspath(__file__))
db_path = 'sqlite:///' + os.path.join(basedir, 'arborator_{}.sqlite'.format(mode))

engine = create_engine(db_path)

def migrate_refactor_github(engine):
    with engine.connect() as connection:
        connection.execute("DELETE FROM github_repositories;")
        connection.execute("DELETE FROM commit_status;")
        
if args.version == 'refactor_github':
    migrate_refactor_github(engine)