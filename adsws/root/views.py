from flask import Blueprint
from adsws import version as v
from flask_login import current_user

blueprint = Blueprint(
    '',
    __name__,
    static_folder="./static",
    template_folder="./templates",
)

@blueprint.route('/', methods=['GET'])
def index():
    return u'Hello %s. This is ADS Web Services API (%s)' % (current_user.email, v.__version__,)

@blueprint.route('/version', methods=['GET'])
def version():
    return v.__version__


