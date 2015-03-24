from flask import request

def scope_func():
  if hasattr(request,'oauth') and request.oauth.client:
    return request.oauth.client.client_id
  return request.remote_addr