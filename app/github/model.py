from sqlalchemy import Column, Integer, String
from app import db  


class GithubRepository(db.Model):
    """Object represents the synchronized github repository"""
    __tablename__ = "github_repositories"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    user_id = Column(String(256), db.ForeignKey("users.id"))  
    repository_name = Column(String(256)) 
    branch = Column(String(256)) # github branch synchronized with AG project
    base_sha = Column(String(256)) # hash of the last commit of the synchronized branch

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self


class GithubCommitStatus(db.Model):
    """entity represents the number of changes that needs to be committed by sample"""
    __tablename__ = "commit_status"
    id = Column(Integer, primary_key=True)
    sample_name = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    changes_number = Column(Integer)

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self
