"""Web interface blueprint with HTML routes"""

from flask import Blueprint, Response
from .templates import INDEX_HTML

bp = Blueprint('web', __name__)


@bp.route('/')
def index():
    """Serve main web interface"""
    return Response(INDEX_HTML, mimetype='text/html')
