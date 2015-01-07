from flask import Flask, jsonify, request

class Stubdata:

  resources_route = {
        "/GET": {
          "description": "desc for resc1",
          "methods": [
            "GET"
          ],
          "scopes": [],
          "rate_limit": [1000,60*60*24],
        },
        "/POST": {
          "description": "desc for resc2",
          "methods": [
            "POST"
          ],
          "scopes": [],
          "rate_limit": [1000,60*60*24],

        },
        "/GETPOST": {
          "description": "desc for resc3",
          "methods": [
            "GET",
            "POST",
          ],
          "scopes": [],
          "rate_limit": [1000,60*60*24],

        },
        "/SCOPED": {
          "description": "desc for resc3",
          "methods": [
            "GET",
          ],
          "scopes": ['this-scope-shouldnt-exist'],
          "rate_limit": [1000,60*60*24],

        },
        "/resources": {
          "description": "Overview of available resources",
          "methods": [
            "GET"
          ],
          "scopes": [],
          "rate_limit": [1000,60*60*24],
        }
      }

  GET = {'resource': 'GET'}
  POST = {'resource': 'POST'}
  GETPOST = {
    'GET': {'resource': 'GETPOST','method':'get'},
    'POST': {'resource': 'GETPOST','method':'post'},
  }




def create_app():
  app = Flask(__name__)

  @app.route('/resources')
  def resources():
    return jsonify(Stubdata.resources_route)

  @app.route('/GET',methods=['GET'])
  def get_():
    return jsonify(Stubdata.GET)

  @app.route('/POST',methods=['POST'])
  def post_():
    return jsonify(Stubdata.POST)

  @app.route('/GETPOST',methods=['GET','POST'])
  def getpost():
    if request.method=='GET':
      return jsonify(Stubdata.GETPOST['GET'])
    if request.method=='POST':
      return jsonify(Stubdata.GETPOST['POST'])

  return app



def run():
  app = create_app()
  app.run(host='127.0.0.1',port=5005,processes=5,debug=False)

if __name__ == "__main__":
  run()