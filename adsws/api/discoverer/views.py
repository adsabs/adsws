from flask import request, current_app
from flask.ext.restful import Resource
from flask.ext.consulate import ConsulService
from urlparse import urljoin
import requests
import json


class ProxyView(Resource):
    """Proxies a request to a remote webservice"""

    def __init__(self, endpoint, service_uri, deploy_path, route):
        self.endpoint = endpoint
        self.service_uri = service_uri
        self.deploy_path = deploy_path
        self.route = route
        self.cs = None
        self.default_request_timeout = current_app.config.get("DEFAULT_REQUEST_TIMEOUT", "60")
        if service_uri.startswith('consul://'):
            self.cs = ConsulService(
                service_uri,
                nameservers=[current_app.config.get("CONSUL_DNS", "172.17.42.1")]
            )
            self.session = self.cs
        else:
            self.session = requests.Session()

    @staticmethod
    def get_body_data(request):
        """
        Returns the correct payload data coming from the flask.Request object
        """
        payload = request.get_json(silent=True)
        if payload:
            return json.dumps(payload)
        return request.form or request.data

    def dispatcher(self, **kwargs):
        """
        Having a dispatch based on request.method solves being able to set up
        ProxyViews on the same resource for different routes. However, it
        limits the ability to scope a resouce on a per-method basis
        """
        path = request.full_path.replace(self.deploy_path, '', 1)
        path = path[1:] if path.startswith('/') else path
        if self.cs is None:
            ep = urljoin(self.service_uri, path)
        else:
            ep = path
        resp = self.__getattribute__(request.method.lower())(ep, request)

        headers = {}
        if resp.headers:
            [headers.update({key: resp.headers[key]}) for key in current_app.config['REMOTE_PROXY_ALLOWED_HEADERS'] if key in resp.headers]

        if headers:
            return resp.text, resp.status_code, headers
        else:
            return resp.text, resp.status_code

    def get(self, ep, request):
        """
        Proxy to remote GET endpoint, should be invoked via self.dispatcher()
        """
        try:
            return self.session.get(ep, headers=request.headers, timeout=self.default_request_timeout)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return b'504 Gateway Timeout', 504

    def post(self, ep, request):
        """
        Proxy to remote POST endpoint, should be invoked via self.dispatcher()
        """
        if not isinstance(request.data, basestring):
            request.data = json.dumps(request.data)
        try:
            return self.session.post(ep, data=ProxyView.get_body_data(request), headers=request.headers, timeout=self.default_request_timeout)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return b'504 Gateway Timeout', 504

    def put(self, ep, request):
        """
        Proxy to remote PUT endpoint, should be invoked via self.dispatcher()
        """
        if not isinstance(request.data, basestring):
            request.data = json.dumps(request.data)
        try:
            return self.session.put(ep, data=ProxyView.get_body_data(request), headers=request.headers, timeout=self.default_request_timeout)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return b'504 Gateway Timeout', 504

    def delete(self, ep, request):
        """
        Proxy to remote PUT endpoint, should be invoked via self.dispatcher()
        """
        if not isinstance(request.data, basestring):
            request.data = json.dumps(request.data)
        try:
            return self.session.delete(ep, data=ProxyView.get_body_data(request), headers=request.headers, timeout=self.default_request_timeout)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return b'504 Gateway Timeout', 504
