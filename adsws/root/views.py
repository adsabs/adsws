from flask import Blueprint
from adsws import version as v

blueprint = Blueprint(
    '',
    __name__,
    static_folder="./static",
    template_folder="./templates",
)

@blueprint.route('/', methods=['GET'])
def index():
    return u'This is ADS Web Services API (%s)' % (v.__version__,)

@blueprint.route('/version', methods=['GET'])
def version():
    return v.__version__


