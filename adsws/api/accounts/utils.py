from exceptions import ValidationError
from flask import request, current_app
import requests

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
    'response': request.json['g-recaptcha-response'] if request.headers.get('content-type','application/json')=='application/json' else request.data['g-recaptcha-response'],
  }
  r = requests.get(ep,params=payload)
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