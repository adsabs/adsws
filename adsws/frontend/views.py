from flask import Blueprint, render_template, request
from adsws.ext.security import login_required
from flask import current_app
from adsws.ext.menu import register_menu

blueprint = Blueprint(
    'frontend',
    __name__,
    static_folder="./static",
    template_folder="./templates",
)

@blueprint.route('/', methods=['GET', 'POST'])
@register_menu(blueprint, 'main.home', 'Home')
def index():
    return render_template('page.html', page_title='hello world')

@blueprint.route('/secret', methods=['GET', 'POST'])
@login_required
@register_menu(blueprint, 'main.secret', 'Protected')
def secret():
    return 'secret'

@blueprint.route('/hello', methods=['GET'])
def hello():
    return '%s' % current_app.config.get('DEBUG')

