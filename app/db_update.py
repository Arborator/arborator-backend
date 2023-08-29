import os
from sqlalchemy import create_engine
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("mode", help="prod or dev")
parser.add_argument("version", help="which commits to migrate (add_github, add_constructicon, all, new_roles)")
args = parser.parse_args()

if args.mode != 'prod' and args.mode != 'dev':
    print('mode must be prod or dev')
    exit()

if args.version != 'add_github' and args.version != 'add_constructicon' and args.version != 'all' and args.version != 'new_roles' and args.version != 'add_validated_tree':
    print('version must be add_github, add_constructicon or all')
    exit()

mode = args.mode
basedir = os.path.dirname(os.path.abspath(__file__))
db_path = 'sqlite:///' + os.path.join(basedir, 'arborator_{}.sqlite'.format(mode))

engine = create_engine(db_path)

def migrate_add_github(engine):
    with engine.connect() as connection:
        #create table github_repositories and commit status
        connection.execute("CREATE TABLE github_repositories (id INTEGER NOT NULL, project_id INTEGER, user_id	VARCHAR(256), repository_name VARCHAR(256), base_sha VARCHAR(256), branch VARCHAR(256), PRIMARY KEY(id), FOREIGN KEY(project_id) REFERENCES projects(id), FOREIGN KEY(user_id) REFERENCES users(id))")
        connection.execute("CREATE TABLE commit_status (id INTEGER NOT NULL, sample_name VARCHAR(256) NOT NULL, project_id INTEGER, changes_number INTEGER, PRIMARY KEY (id),  FOREIGN KEY(project_id) REFERENCES projects (id))")

        #update users table

        connection.execute('ALTER TABLE users ADD github_access_token VARCHAR(256)')
        connection.execute('ALTER TABLE users ADD email VARCHAR(60)')
        connection.execute('ALTER TABLE users ADD not_share_email BOOLEAN')
        connection.execute('ALTER TABLE users ADD receive_newsletter BOOLEAN')
        connection.execute('UPDATE users SET email = id WHERE users.auth_provider == 3')

        #update projects table
        connection.execute('ALTER TABLE projects ADD freezed BOOLEAN')


def migrate_add_constructicon(engine):
    with engine.connect() as connection:
        # add constructicon table
        # connection.execute('CREATE TABLE constructicon (id UUID PRIMARY KEY, title TEXT NOT NULL, description TEXT, structure TEXT NOT NULL, structure_verbose TEXT, grew_query TEXT NOT NULL, tags JSONB, project_id UUID, FOREIGN KEY (project_id) REFERENCES project(id));')
        connection.execute('CREATE TABLE constructicon ( id UUID PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, grew_query TEXT NOT NULL, tags JSONB NOT NULL, project_id INTEGER NOT NULL, FOREIGN KEY (project_id) REFERENCES projects(id));')

def migrate_new_roles(engine):
    with engine.connect() as connection:
        connection.execute('UPDATE projectaccess SET access_level = 3 WHERE projectaccess.access_level == 2')
           

def migrate_add_validated_tree(engine):
    with engine.connect() as connection:
        connection.execute('ALTER TABLE projects RENAME COLUMN exercise_mode To blind_annotation_mode')
        connection.execute('ALTER TABLE projects ADD config STRING') 
        connection.execute('ALTER TABLE projects DROP show_all_trees')  
        connection.execute('ALTER TABLE exerciselevel RENAME COLUMN exercise_level TO blind_annotation_level')
        connection.execute('ALTER TABLE exerciselevel RENAME TO blindannotationlevel')
        connection.execute('CREATE TABLE user_tags (id INTEGER NOT NULL, user_id VARCHAR(256), tags JSONB, PRIMARY KEY(id), FOREIGN KEY(user_id) REFERENCES users(id))')
        

if args.version == 'add_github':
    migrate_add_github(engine)

if args.version == 'add_constructicon':
    migrate_add_constructicon(engine)

if args.version == 'all':
    migrate_add_github(engine)
    migrate_add_constructicon(engine)

if args.version == 'new_roles':
    migrate_new_roles(engine)

if args.version == 'add_validated_tree':
    migrate_add_validated_tree(engine)