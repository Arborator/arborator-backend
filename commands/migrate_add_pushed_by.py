from sqlalchemy import text

from app import db


def migrate_add_pushed_by():
    result = db.session.execute(text("PRAGMA table_info(staged_trees)")).fetchall()
    columns = [row[1] for row in result]

    if 'pushed_by' in columns:
        print("Column pushed_by already exists")
        return

    db.session.execute(text("ALTER TABLE staged_trees ADD COLUMN pushed_by VARCHAR(255)"))
    db.session.commit()
    print("Column pushed_by added")