import os

from app import create_app

from dotenv import load_dotenv
load_dotenv(dotenv_path=".flaskenv", verbose=True)

env = os.getenv("FLASK_ENV") or "test"

app = create_app(env)
if __name__ == "__main__":
    app.run("0.0.0.0", 8080, debug=True)
