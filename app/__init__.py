from .config import SECRET_KEY
from flask import Flask

app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET_KEY
app.config.from_envvar('DEV_SETTINGS', silent=True)

from app import tools
from app import routes
