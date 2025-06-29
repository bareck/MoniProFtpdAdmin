from flask import Blueprint

bp = Blueprint('groups', __name__)

from . import routes