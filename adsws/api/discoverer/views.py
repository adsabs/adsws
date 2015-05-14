from flask import jsonify, request
from flask.ext.restful import Resource
from werkzeug.datastructures import Headers
from urlparse import urljoin
import requests
import json



class ProxyView(Resource):
    """Proxies a request to a remote webservice"""

    def __init__(self, endpoint, service_uri, deploy_path):
        self.endpoint = endpoint
        self.service_uri = service_uri
        self.deploy_path = deploy_path

    def dispatcher(self, **kwargs):
        """
        Having a dispatch based on request.method solves being able to set up
        ProxyViews on the same resource for different routes. However, it
        limits the ability to scope a resouce on a per-method basis
        """
        path = request.full_path.replace(self.deploy_path, '', 1)
        path = path[1:] if path.startswith('/') else path
        ep = urljoin(self.service_uri, path)
        h = Headers(request.headers.items())
        h.setdefault('X-Adsws-Uid', request.oauth.user.id)
        request.headers = h
        return self.__getattribute__(request.method.lower())(ep, request)

    def get(self, ep, request):
        """
        Proxy to remote GET endpoint, should be invoked via self.dispatcher()
        """
        r = requests.get(ep, headers=request.headers)
        return jsonify(r.json())

    def post(self, ep, request):
        """
        Proxy to remote POST endpoint, should be invoked via self.dispatcher()
        """
        if not isinstance(request.data, basestring):
            request.data = json.dumps(request.data)
        r = requests.post(ep, data=request.data, headers=request.headers)
        resp = r.json()

        # This should only be necessary for httpretty in unittests
        if isinstance(resp, basestring):
            resp = json.loads(resp)
        return jsonify(resp)

    def put(self, ep, request):
        """
        Proxy to remote PUT endpoint, should be invoked via self.dispatcher()
        """
        if not isinstance(request.data, basestring):
            request.data = json.dumps(request.data)
        r = requests.put(ep, data=request.data, headers=request.headers)
        resp = r.json()

        # This should only be necessary for httpretty in unittests
        if isinstance(resp, basestring):
            resp = json.loads(resp)
        return jsonify(resp)
