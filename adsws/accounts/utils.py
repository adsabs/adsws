import datetime
import requests
from functools import wraps

from flask import current_app, session
from flask_mail import Message
from flask_login import current_user as cu
from flask_login import logout_user as flask_logout_user

from .exceptions import ValidationError
from .emails import Email


def logout_user():
    """
    Logs out the user from a Flask session, and does some extra functionality on top of it, that is not
    done normally by Flask-login

    :return: message from Flask-login logout_user
    """

    expunge_list = ['oauth_client']

    message = flask_logout_user()
    [session.pop(item, None) for item in expunge_list]

    return message


def get_post_data(request):
    """
    Attempt to coerce POST json data from the request, falling
    back to the raw data if json could not be coerced.
    :type request: flask.request
    """
    try:
        return request.get_json(force=True)
    except:
        return request.values


def send_email(email_addr='', base_url='', email_template=Email, payload=None):
    """
    Encrypts a payload using itsDangerous.TimeSerializer, adding it along with a base
    URL to an email template. Sends an email with this data using the current app's
    'mail' extension.

    :param email_addr:
    :type email_addr: basestring
    :param base_url: endpoint url that is passed to the email templace
    :type base_url: basestring
    :type email_template: utils.Email
    :param payload: payload to encrypt, joined with ' '. __str__() should return url-safe string

    :return: msg,token
    :rtype flask_mail.Message, basestring
    """
    if payload is None:
        payload = []
    if isinstance(payload, (list, tuple)):
        payload = ' '.join(map(str, payload))
    token = current_app.ts.dumps(payload, salt=email_template.salt)
    endpoint = '{url}/{token}'.format(url=base_url, token=token)
    msg = Message(subject=email_template.subject,
                  recipients=[email_addr],
                  body=email_template.msg_plain.format(endpoint=endpoint),
                  html=email_template.msg_html.format(endpoint=endpoint,email_address=email_addr))
    current_app.extensions['mail'].send(msg)
    return msg, token


def verify_recaptcha(request, ep=None):
    """
    Verify a google recaptcha based on the data contained in the request

    :param request: flask.request
    :param ep: google recaptcha endpoint
    :type ep: basestring|None
    :return:True|False
    """
    if ep is None:
        ep = current_app.config['GOOGLE_RECAPTCHA_ENDPOINT']
    data = get_post_data(request)
    payload = {
        'secret': current_app.config['GOOGLE_RECAPTCHA_PRIVATE_KEY'],
        'remoteip': request.remote_addr,
        'response': data['g-recaptcha-response']
    }
    try:
        r = requests.post(ep,data=payload, timeout=60)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False
    r.raise_for_status()
    return True if r.json()['success'] == True else False


def validate_email(email):
    """
    Validate that an email is properly formatted.
    This minimal validation requires that an "@"
    be present and no spaces be present in the string

    :param email: basestring
    :return: True|Exception:ValidationError
    """

    if '@' not in email or ' ' in email:
        # This minimal validation is OK, since we validate the email with a
        # link anyways
        raise ValidationError('Not a valid email')
    return True


def validate_password(password):
    """
    Password must have one lowercase letter, one uppercase letter and one digit.
    Inspired/reused from lingthio/Flask-User.

    :type password: basestring
    """
    if len(password) < 4:
        raise ValidationError('Password must have at least 4 characers')

    return True


def login_required(func):
    """
    If you decorate a view with this, it will ensure that the current user is
    logged in and authenticated before calling the actual view. (If they are
    not, it calls the :attr:`LoginManager.unauthorized` callback.) For
    example::
        @app.route('/post')
        @login_required
        def post():
            pass
    If there are only certain times you need to require that your user is
    logged in, you can do so with::
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
    ...which is essentially the code that this function adds to your views.
    It can be convenient to globally turn off authentication when unit
    testing. To enable this, if either of the application
    configuration variables `LOGIN_DISABLED` or `TESTING` is set to
    `True`, this decorator will be ignored.

    *Note*: copy/past of flask_login function with added conditional that
    checks that our user isn't the bumblebee user

    :param func: The view function to decorate.
    :type func: function
    """

    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_app.login_manager._login_disabled:
            return func(*args, **kwargs)
        elif not cu.is_authenticated() or \
                cu.email == current_app.config['BOOTSTRAP_USER_EMAIL']:
            return current_app.login_manager.unauthorized()
        return func(*args, **kwargs)
    return decorated_view


def print_token(token):
    """
    Formats the data in current_user and token to the format
    expected by the bumblebee javascript client

    :param token: OAuthToken instance
    :return: dict containing string info
    """
    expiry = token.expires.isoformat() if \
        isinstance(token.expires, datetime.datetime) else token.expires
    anon = True if cu.email == current_app.config['BOOTSTRAP_USER_EMAIL'] \
        else False
    return {
        'access_token': token.access_token,
        'refresh_token': token.refresh_token,
        'username': cu.email,
        'expire_in': expiry,
        'token_type': 'Bearer',
        'scopes': token.scopes,
        'anonymous': anon
    }
