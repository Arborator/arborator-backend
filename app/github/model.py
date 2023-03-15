from sqlalchemy import Column, Integer, String

from app import db  


class GithubRepository(db.Model):
    __tablename__ = "github_repositories"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    user_id = Column(String(256), db.ForeignKey("users.id")) 
    repository_name = Column(String(256)) 

