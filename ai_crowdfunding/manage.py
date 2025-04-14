from flask_migrate import Migrate
from flask import current_app
from app import create_app, db

app = create_app('development')
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run() 