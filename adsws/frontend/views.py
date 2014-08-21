from flask import Blueprint, render_template, request
from adsws.ext.security import login_required

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