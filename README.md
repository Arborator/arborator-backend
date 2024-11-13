# Example of a scalable Flask API

This the back-end of the Arborator-Grew redevelopement of the arborator-server.

## Useful Resources
Before starting to dive deep in the code, you should refer to these following important resources :
- [Flask-RESTx](https://flask-restx.readthedocs.io/en/latest/) : How to build a restful server with python
- [Some Flask good practives](http://alanpryorjr.com/2019-05-20-flask-api-example/) : How to use static typing and testing procedure with flask.

## Setting the environment config
Create a .flaskenv file with the following config 
```
FLASK_ENV=dev|prod|test
```

## Run the backend
To run the backend we use the docker, the steps of the docker installation are [here](https://github.com/Arborator/arborator-frontend#1-install-docker-and-docker-compose)

- To ensure the communication between the containers of the backend and the frontend we need to create network
```
docker network create external-network
```
- Run the container of the backend using docker-compose
```
docker-compose up --build
```


## Handle keys + auth_config
Ask an admin of Arborator the keys.zip and the auth_config.py, and locate them in (from root)
```
app/auth/auth_config.py
keys/
```

### Manage the database

If first time, initialize the database

```
python manage.py seed_db
```

Type "Y" to accept the message (which is just there to prevent you accidentally deleting things -- it's just a local SQLite database)

#### Database automatic migration

An migration is set using [Flask-Migrate](https://flask-migrate.readthedocs.io/en/latest/). For the moment this migration should only be done on dev mode.

To enable the migrations run the following commands after the git pull:
```flask db init```
The register it and enabling automatic migrations by setting a name (here it is "access migration")
```flask db migrate -m "access migration."``` 
Apply the migration
```flask db upgrade```

This migration adds a table `alembic_version` in the database in order to track migration history. 
To display migration history please run `flask db history`.


### Handling superadmin
For adding a superadmin, run the following command
```
python manage.py add_super_admin --username $username
```

For removing a superadmin
```
python manage.py remove_super_admin --username $username
```


### Run the app for local development

In .flaskenv, set the `FLASK_ENV` to dev and `FLASK_APP` to wsgi.py
There is two other variables `MAIL_USERNAME` and `MAIL_PASSWORD` that you need to set with your email address and password in order to user `Flask-Mail` library
```
FLASK_ENV=dev
FLASK_APP=wsgi.py
```


Then, you can run the app with flask and a secured certificate protocole.
```
flask run --cert=adhoc
```
We need to specify `cert` because we use Google and Github credentials login and it required an https connection.

## Running tests

To run the test suite, simply pip install it and run from the root directory like so

```
pip install pytest
pytest
```


### Production

#### Pulling last changes on prod
1) ssh to server
2) go to backend folder
3) pull latests changes : `git pull origin main`
4) restart service : `sudo systemctl restart arborator-backend.service`
#### Deploy the app in production for the first time

##### Set the environment

On the server, create the project folder

```
mkdir /var/www/flask_api_example
```

In the project folder, create a python virtual environment
```
python -m venv ven
```

Install the python packages requirements
```
pip install -r requirements.txt
```

In .flaskenv, set `FLASK_ENV` to prod
```
FLASK_ENV=prod
```

Initialize the DB (or paste an existant one)
```
python migrate.py seed_db
```

##### Proxy setting 

If needed to, allow the folder access to the server user that will have control the app
```
sudo chown -Rf <admin>:<group> /var/www/flask_api_example/
```

##### Debugging and logging
To see the arborator logs : 
```
tail -f /var/log/arborator-backend/arborator-backend.log
```
To see tge nginx logs :
```
sudo tail -f /var/log/nginx/access.log
```
To see all last commands run on the server :
```
history
```


source : https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uswgi-and-nginx-on-ubuntu-18-04

Navigate to the posted URL in your terminal to be greeted with Swagger, where you can test out the API.


