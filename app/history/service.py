from typing import List

from flask_login import current_user

from app import db
from .model import History


class HistoryService: 

    @staticmethod
    def get_all_user_history(project_id) -> List[History]:
        """Get all user history

        Args:
            project_id (int)

        Returns:
            List[History]
        """
        return History.query.filter_by(project_id=project_id, user_id=current_user.id).all()
    
    @staticmethod 
    def get_by_uuid(project_id, uuid) -> History:
        """Get specific history entry using uuid

        Args:
            project_id (int)
            uuid (str)

        Returns:
            History
        """
        return History.query.filter_by(project_id=project_id, uuid= uuid).first()

    @staticmethod
    def create(new_attrs) -> History:
        """Create new user entry

        Args:
            new_attrs (dict)
        Returns:
            History
        """
        new_history_record = History(**new_attrs)
        db.session.add(new_history_record)
        db.session.commit()
        return new_history_record
    
    @staticmethod
    def delete_by_id(record_id): 
        """Delete history entry by id

        Args:
            record_id (int)
        """
        History.query.filter_by(id=record_id).delete()
        db.session.commit()
    
    @staticmethod
    def delete_all_history(project_id):
        """
            Delete all user history
        Args:
            project_id (int)
        """
        History.query.filter_by(project_id=project_id, user_id=current_user.id).delete()
        db.session.commit()

    @staticmethod
    def update(history_record: History, new_attrs) -> History:
        """Update history record 

        Args:
            history_record (History)
            new_attrs (dict(HistoryInterface))

        Returns:
            History
        """
        if history_record:
            history_record.update(new_attrs)
            db.session.commit()
            return history_record

