import sqlite3, sqlalchemy_utils

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine


# mode = 'prod'
mode = 'dev'
engine = create_engine('sqlite://///home/marine/Téléchargements/fixbug/arborator_{}_old.sqlite'.format(mode))
with engine.connect() as connection:
    # create a new table without is_open and is_private, and with is_visible instead
    connection.execute('''CREATE TABLE projectss (id INTEGER NOT NULL PRIMARY KEY, project_name VARCHAR(256) NOT NULL UNIQUE, description VARCHAR(256), image BLOB, show_all_trees BOOLEAN, visibility INTEGER)''')
    # insert data from the old table
    connection.execute('''INSERT INTO projectss (id, project_name, description, image, show_all_trees) SELECT id, project_name, description, image, show_all_trees FROM projects''')
    
    # set the visibility based on old columns
    connection.execute('''UPDATE projectss SET visibility = 0 WHERE projectss.id IN (SELECT id from projects WHERE projects.is_private=1)''')
    connection.execute('''UPDATE projectss SET visibility = 1 WHERE projectss.id IN (SELECT id from projects WHERE projects.is_private=0 AND projects.is_open=0)''')
    connection.execute('''UPDATE projectss SET visibility = 2 WHERE projectss.id IN (SELECT id from projects WHERE projects.is_private=0 AND projects.is_open=1)''')
    
    # delete the old table
    connection.execute('''DROP TABLE projects''')

    # rename the table
    connection.execute('''ALTER TABLE projectss RENAME TO projects''')

    # create the new tables
    connection.execute('''CREATE TABLE feature (id INTEGER NOT NULL PRIMARY KEY, project_id INTEGER, value VARCHAR(256) NOT NULL)''')
    connection.execute('''CREATE TABLE metafeature (id INTEGER NOT NULL PRIMARY KEY, project_id INTEGER, value VARCHAR(256) NOT NULL)''')
    
    results = connection.execute('''SELECT id from projects''')

    # adding default shown features
    for id, row in enumerate(results):
        connection.execute('''INSERT INTO metafeature (id, project_id, value) VALUES ({}, {}, 'sent_id')'''.format(id, row[0]))
        connection.execute('''INSERT INTO feature (id, project_id, value) VALUES ({}, {}, 'LEMMA')'''.format(id, row[0]))
