from exceptions import ValidationError
from flask import request, current_app, url_for
from flask.ext.mail import Message
import requests

def get_post_data(request):
  try:
    return request.get_json()
  except:
    return request.values

def send_password_reset_email(email,url=None,msg=None):
  token = current_app.ts.dumps(email,salt='reset-email')
  if msg is None:
    endpoint = '{url}/{token}'.format(url=url,token=token)
    msg = Message(
          subject="[ADS] Password reset",
          recipients=[email],
          html='''
Hi,

Someone (probably you) has requested a password reset on the account associated with this email address.

To reset your password, please visit
<a href="{endpoint}">{endpoint}</a> with your browser.

This link will be valid for the next 10 minutes.

If this is a mistake, then just ignore this email.

-The ADS team'''.format(endpoint=endpoint))
  current_app.extensions['mail'].send(msg)
  return msg, token

def send_verification_email(email, url=None, msg=None):
  token = current_app.ts.dumps(email,salt='verification-email')
  if msg is None:
    endpoint = '{url}/{token}'.format(url=url,token=token)
    msg = Message(
          subject="[ADS] Please verify your email address",
          recipients=[email],
          html='''
Hi,

Someone (probably you) has registered this email address with the NASA-ADS (http://adslabs.org).

To confirm this action, please visit
<a href="{endpoint}">{endpoint}</a> with your browser.

If this is a mistake, then just ignore this email.

-The ADS team'''.format(endpoint=endpoint))
  current_app.extensions['mail'].send(msg)
  return msg, token

def scope_func():
  if hasattr(request,'oauth') and request.oauth.client:
    return request.oauth.client.client_id
  return request.remote_addr

def verify_recaptcha(request,ep=None):
  if ep is None:
    ep = current_app.config['GOOGLE_RECAPTCHA_ENDPOINT']

  payload = {
    'secret': current_app.config['GOOGLE_RECAPTCHA_PRIVATE_KEY'],
    'remoteip': request.remote_addr,
    'response': request.json['g-recaptcha-response'] if request.headers.get('content-type','application/json')=='application/json' else request.form['g-recaptcha-response'],
  }
  r = requests.post(ep,data=payload)
  r.raise_for_status()
  return True if r.json()['success'] == True else False

def validate_email(email):
  if '@' not in email:
    #This minimal validation is OK, since we validate the email with a link anyways
    raise ValidationError('Not a valid email')
  return True

def validate_password(password):
  """ Password must have one lowercase letter, one uppercase letter and one digit.
  Inspired/reused from lingthio/Flask-User
  """
  password_length = len(password)

  # Count lowercase, uppercase and numbers
  lowers = uppers = digits = 0
  for ch in password:
    if ch.islower(): lowers+=1
    if ch.isupper(): uppers+=1
    if ch.isdigit(): digits+=1

  # Password must have one lowercase letter, one uppercase letter and one digit
  is_valid = password_length>=6 and lowers and uppers and digits
  if not is_valid:
    raise ValidationError('Password must have at least 6 characters with one lowercase letter, one uppercase letter and one number')
  return True

