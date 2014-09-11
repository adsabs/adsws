from flask import Blueprint, render_template, request
from adsws.ext.security import login_required
from flask import current_app
from adsws.ext.menu import register_menu
from flask.ext.login import current_user
from adsws import version as v

blueprint = Blueprint(
    'frontend',
    __name__,
    static_folder="./static",
    template_folder="./templates",
)

@blueprint.route('/', methods=['GET', 'POST'])
@register_menu(blueprint, 'ui.home', 'Home')
def index():
    return u'Hello %s. This is ADS Web Services API (%s)' % \
    (current_user.is_authenticated() and current_user.email or 'Anonymous', v.__version__,)

@blueprint.route('/secret', methods=['GET', 'POST'])
@login_required
@register_menu(blueprint, 'main.secret', 'Protected')
def secret():
    return 'secrets'

@blueprint.route('/hello', methods=['GET'])
def hello():
    return '%s' % current_app.config.get('DEBUG')

