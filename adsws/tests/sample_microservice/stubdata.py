class Stubdata:
    GET = {'resource': 'GET'}
    POST = {'resource': 'POST'}
    GETPOST = {
        'GET': {'resource': 'GETPOST', 'method': 'get'},
        'POST': {'resource': 'GETPOST', 'method': 'post'},
    }
