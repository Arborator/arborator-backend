from app import db

def seed_database():
    """Seed the DB."""
    import click

    if click.confirm("Are you sure you want to drop all tables and recreate?"):
        print("Dropping tables...")
        db.drop_all()
        db.create_all()
        # seed_things()
        db.session.commit()
        print("DB successfully seeded.")
    else:
        print("Aborted.")