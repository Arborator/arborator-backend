import os

from app import create_app

from app.socket_init import socketio

from dotenv import load_dotenv
load_dotenv(dotenv_path=".flaskenv", verbose=True)

env = os.getenv("FLASK_ENV") or "test"

app = create_app(env)
socketio.init_app(app)

if __name__ == "__main__":
    socketio.run(app, port=3000)
    # app.run("0.0.0.0", 8080, debug=True)
