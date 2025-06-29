from flask import Blueprint

bp = Blueprint('monitoring', __name__)

from . import routes