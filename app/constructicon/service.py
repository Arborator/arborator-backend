from app import db

from app.constructicon.model import Constructicon


class ConstructiconService:
    @staticmethod
    def get_by_id(entryId: str) -> Constructicon:
        return Constructicon.query.get(entryId)

    @staticmethod
    def delete_by_id(entryId: str):
        Constructicon.query.filter_by(id=entryId).delete()
        db.session.commit()

    @staticmethod
    def get_all_by_project_id(project_id):
        return Constructicon.query.filter_by(project_id=project_id).all()

    @staticmethod
    def create(new_attrs) -> Constructicon:
        new_constructicon_entry = Constructicon(**new_attrs)
        db.session.add(new_constructicon_entry)
        db.session.commit()
        return new_constructicon_entry

    @staticmethod
    def create_or_update(new_attrs):
        entry_if_exists = ConstructiconService.get_by_id(new_attrs["id"])
        if entry_if_exists:
            print("KK updating values in db")
            entry_if_exists.update(new_attrs)
            db.session.commit()
            return entry_if_exists
        else:
            return ConstructiconService.create(new_attrs)

