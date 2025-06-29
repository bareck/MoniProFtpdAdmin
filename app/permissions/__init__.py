from flask import Blueprint

bp = Blueprint('permissions', __name__)

from . import routes