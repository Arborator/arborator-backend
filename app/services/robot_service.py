import os
import json
import zipfile
import time
import io
from ..models.models import *
from ..repository import project_dao, user_dao, robot_dao


def create_or_get_robot_for_project(name, project_id):
    ''' create or retireve robot for a given project '''
    r = robot_dao.find_by_name_and_project_id(name, project_id)
    if r:
        return r
    else:
        return robot_dao.add(name, project_id)


def get_by_name_and_project_id(name, project_id):
    ''' get a robot by its name and project_id '''
    return robot_dao.find_by_name_and_project_id(name, project_id)


def get_by_project_id(project_id):
    ''' get robots linked to a project '''
    return robot_dao.find_by_project_id(project_id)


def get_by_id(id):
    ''' get by id '''
    return robot_dao.find_by_id(id)


def get_by_project_id_userlike(project_id):
    ''' get robots linked to a project '''
    robots = robot_dao.find_by_project_id(project_id)
    robots = [r.as_json(include={'auth_provider': None, 'family_name': None, 'first_name': None,
                                 'last_seen': None, 'super_admin': False, 'robot': True}) for r in robots]
    # for r in robots: r['username'] = r['name']
    return robots
