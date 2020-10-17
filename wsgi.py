import os

from app import create_app

app = create_app(os.getenv("FLASK_ENV") or "test")
if __name__ == "__main__":
    app.run("0.0.0.0", 8080, debug=True)
