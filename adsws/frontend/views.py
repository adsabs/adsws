from flask import Blueprint, render_template, request
from adsws.ext.security import login_required
from flask import current_app

blueprint = Blueprint(
    'frontend',
    __name__,
    static_folder="./static",
    template_folder="./templates",
)

@blueprint.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    return 'hello world'

@blueprint.route('/hello', methods=['GET'])
def hello():
    return '%s' % current_app.config.get('DEBUG')

