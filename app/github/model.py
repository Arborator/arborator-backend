from sqlalchemy import Column, Integer, String, Boolean
from app import db  


class GithubRepository(db.Model):
    __tablename__ = "github_repositories"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    user_id = Column(String(256), db.ForeignKey("users.id")) 
    repository_name = Column(String(256)) 


class GithubCommitStatus(db.Model):
    __tablename__ = "commit_status"
    id = Column(Integer, primary_key=True)
    sample_name = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    changes_number = Column(Integer)

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self
