# Example of a scalable Flask API

This the back-end of the Arborator-Grew redevelopement of the arborator-server.

## Useful Resources
Before starting to dive deep in the code, you should refer to these following important resources :
- [Flask-RESTx](https://flask-restx.readthedocs.io/en/latest/) : How to build a restful server with python
- [Some Flask good practives](http://alanpryorjr.com/2019-05-20-flask-api-example/) : How to use static typing and testing procedure with flask.

## Setting the project 
### Setting the environment config
Create a .flaskenv file with the following config 
```
FLASK_ENV=dev|prod|test
FLASK_APP=wsgi.py
MAIL_USERNAME='useremail@address.com' # this email is used in order to use  flask-email library
MAIL_PASSWORD='useremail password'

```
### Handle keys + auth_config
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

### Database automatic migration

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
python manage.py remove_super_admin --username $username#
```


## Run the backend for local development
In .flaskenv, set the `FLASK_ENV` to dev

### Run the project without docker 

Create virtual environment et install the libraries.
```
python -m venv ven
source venv/bin/activate
pip install -r requirements.txt
```
Then, you can run the app with flask and a secured certificate protocole.
```
flask run --cert=adhoc
```
We need to specify `cert` because we use Google and Github credentials login and it required an https connection.

### Run the project using the docker
To run the backend we use the docker, the steps of the docker installation are [here](https://github.com/Arborator/arborator-frontend#1-install-docker-and-docker-compose)

- To ensure the communication between the containers of the backend and the frontend we need to create network
```
docker network create external-network
```
- Run the container of the backend using docker-compose
```
docker-compose up --build
```
## Production 

### Install Nginx and configure web server
First we need to install a web server in our case we are using Nginx. 
```
sudo apt update
sudo apt install nginx
```
Create config file for ArboratorGrew.

```
sudo nano /etc/nginx/sites-available/arborator

```
Add the following content.

```
server {
    server_name arboratorgrew.com # use your servername
	
    location / {

        root /path/to/arborator-frontend/dist/spa;
    }

    location /parser/ {
      proxy_pass path/to/parser;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
    }

    location ~ ^/(api|login|media|socket.io)/{
        include uwsgi_params;
        uwsgi_read_timeout 600s;
        uwsgi_pass unix:/path/to/arborator-backend/arborator-backend.sock;
        client_max_body_size 100M; 
    }
}

```
Secure the application using let's encrypt.

```
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d arboratorgrew.com -d www.arboratorgrew.com
```
Enable the configuration.

```
sudo ln -s /etc/nginx/sites-available/arborator /etc/nginx/sites-enabled/
```

Test the configuration and reload nginx. 

```
sudo nginx -t 
sudo systemctl reload nginx
```
### Configure ArboratorGrew project

Create folders for arborator-frontend and backend. 
```
mkdir arborator-frontend arborator-backend
```
Clone the backend.

```
git clone https://github.com/Arborator/arborator-backend.git
```
Set the environement and install requirements.

```
python -m venv ven
source venv/bin/activate
pip install -r requirements.txt
pip install uwsgi   # this package is installed only for the prod 
uwsgi --ini arborator-backend.ini # create .sock file for wsgi

```
In .flaskenv, set `FLASK_ENV` to prod
```
FLASK_ENV=prod
```
In ArboratorGrew, we have the possibility to use [UD validator](https://github.com/UniversalDependencies/tools/blob/master/validate.py). This script uses [data folder](https://github.com/UniversalDependencies/tools/tree/master/data) that's usually updated by UD community. In order to get the updated version, we set up a cron job that runs the script  `/fetch_validator_data.sh`. To do so

```
crontab -e
```
Add the line below, in the crontab file 

```
0 4 * * * /path/to/arborator-backend/fetch_validator_data.sh
```
### Run the application as service with systemd

In order to run the application on the server we need to create a systemd service file. 

Create a service file `arborator-backend.service` 
```
sudo nano /etc/systemd/system/arborator-backend.service
```
Add configuration to the service file. 

```
[Unit]
Description=uWSGI instance to serve ArboratorGrew
After=network.target

[Service]
User=yourusername
Group=yourgroupusername
WorkingDirectory=/path/to/arborator-backend
Environment="PATH=/path/to/arborator-backend/venv/bin"
ExecStart=/path/to/arborator-backend/venv/bin/uwsgi --ini arborator-backend.ini

[Install]
WantedBy=multi-user.target
```

Enable and start the service.

```
# Reload the systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service 
sudo systemctl enable arborator-backend.service

# Start the service
sudo systemctl start arborator-backend.service
```

### Github actions configuration 

Generate SSH key pair to connect with Github Actions.

```
ssh-keygen -t rsa -b 4096 -C "actions@github.com"

# After that choose where to save the key /path/to/github-actions_key
```
Add public key to the remote server.

```
ssh-copy-id -i /path/to/github-actions_key  user@server_ip
```

Add private key and other secret variables to Github actions secrets. 

- Navigate to **Settings > Secrets and variables > Actions**
- Add **New respository secret** with this names.

```
SERVER_HOST

SERVER_PORT

SERVER_SSH_KEY 

SERVER_USERNAME
```
In order to run the pipeline we need to run `arborator-backend.service` with passwordless sudo, to do so we need change the `sudoers` file.
```
sudo visudo
```
Add new permissions to the `sudoers` file. 

```
user ALL=(ALL:ALL) NOPASSWD: /bin/systemctl restart arborator-backend.service

```
Save the changes after the edit using `visudo`

##### Debugging and logging
To see the arborator logs : 
```
tail -f /var/log/arborator-backend/arborator-backend.log
```
To see the nginx logs :
```
sudo tail -f /var/log/nginx/access.log
```


## Running tests

To run the test suite, simply pip install it and run from the root directory like so

```
pip install pytest
pytest
```



