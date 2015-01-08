import os
from flask import Blueprint
from flask import Flask, g
from views import Resources, GET, POST, GETPOST, SCOPED, LOW_RATE_LIMIT
from flask.ext.restful import Api

def _create_blueprint_():
  return Blueprint(
      'sample_application',
      __name__,
      static_folder=None,
  )

def create_app(blueprint_only=False):
  app = Flask(__name__, static_folder=None)

  app.url_map.strict_slashes = False
  app.config.from_pyfile('config.py')
  try:
    app.config.from_pyfile('local_config.py')
  except IOError:
    pass

  #Ugly hack for testings: blueprint needs to be destroyed 
  #between tests, otherwise _registered_once=False 
  #will cause app.register_blueprint to fail
  #reload(views)
  bp = _create_blueprint_()
  api = Api(bp)

  api.add_resource(Resources, '/resources')
  api.add_resource(GET, '/GET')
  api.add_resource(POST,'/POST')
  api.add_resource(GETPOST,'/GETPOST')
  api.add_resource(SCOPED,'/SCOPED')
  api.add_resource(LOW_RATE_LIMIT,'/LOW_RATE_LIMIT')

  if blueprint_only:
    return bp
  app.register_blueprint(bp)
  return app

def run():
  app = create_app()
  app.run(host='127.0.0.1',port=5005,processes=5,debug=False)

if __name__ == "__main__":
  run()