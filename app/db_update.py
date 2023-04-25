import os
from sqlalchemy import create_engine


mode = 'dev'
basedir = os.path.dirname(os.path.abspath(__file__))
db_path = 'sqlite:///' + os.path.join(basedir, 'arborator_{}.sqlite'.format(mode))

engine = create_engine(db_path)
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
    