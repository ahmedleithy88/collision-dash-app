# wsgi.py
from app import app

# This makes the app callable for Gunicorn
application = app.server

if __name__ == "__main__":
    application.run()
