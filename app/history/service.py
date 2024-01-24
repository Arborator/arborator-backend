from typing import List

from flask_login import current_user

from app import db
from .model import History


class HistoryService: 

    @staticmethod
    def get_all_user_history(project_id) -> List[History]:
        print(History.query.filter_by(project_id=project_id, user_id=current_user.id).all())
    
    @staticmethod
    def create(new_attrs) -> History:
        new_history_record = History(**new_attrs)
        db.session.add(new_history_record)
        db.session.commit()
        return new_history_record
    
    @staticmethod
    def delete_by_id(record_id): 
        History.query.filter_by(id=record_id).delete()
        db.session.commit()
    
    @staticmethod
    def delete_all_history(project_id):
        History.query.filter_by(project_id=project_id, user_id=current_user.id).delete()
        db.session.commit()

    @staticmethod
    def update(new_attrs) -> History:
        history_record = History.query.filter_by(new_attrs.get("id"))
        if history_record:
            history_record.update(new_attrs)
            db.session.commit()
            return history_record

