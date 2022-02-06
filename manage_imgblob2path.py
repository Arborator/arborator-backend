import os
from flask_script import Manager

from app import create_app, db
from commands.seed_command import SeedCommand


from dotenv import load_dotenv
load_dotenv(dotenv_path=".flaskenv", verbose=True)
from sqlalchemy import MetaData, Table, Column, Integer, String

env = os.getenv("FLASK_ENV") or "test"
print(f"Active environment: * {env} *")
app = create_app(env)

manager = Manager(app)
app.app_context().push()
manager.add_command("blob2img", SeedCommand)

#### to run as follows
# ########################  python3 manage_imgblob2path.py blob_to_path ####################



@manager.command
def run():
    app.run()


@manager.command
def blob_to_path():
    '''exports all the blob images to png files and replace the content by their path'''
    
    import subprocess

    subprocess.run(['bash', 'migrate_img.sh', 'app/arborator_dev.sqlite', '../arborator-frontend/public/images/projectimages']) #, 'y'])
    # subprocess.run(['bash', 'migrate_img.sh', 'app/20220206.arborator_prod.sqlite', 'images_prod_temp'])#'../arborator-frontend/public/images/projectimages']) #, 'y'])
    # prod
    subprocess.run(['bash', 'migrate_img.sh', 'app/arborator_dev.sqlite', '/home/arborator/arborator-frontend/dist/spa/images/projectimages']) #, 'y'])
    # print('Retrieved all Blob based images from database to app/public/projectimages as png files named according to the project name')

    from app.projects.service import ProjectService
    from app.projects.model import Project
    projects = ProjectService.get_all()
    print('Will now process the %s projects with a custom image' % (len([ (p.project_name, p.image) for p in projects if p.image is not None])))
    for p in projects:
        if p.image is not None: ProjectService.change_image(p.project_name, 'images/projectimages/%s.png' % (p.project_name) )
    print('Images changed with the relative png file path')


if __name__ == "__main__":
    manager.run()
