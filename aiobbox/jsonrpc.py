import re
from aiobbox.exceptions import DataError

def parse_method(method):
    return re.match(
        r'(?P<srv>\w[\.\w]*)::(?P<method>\w+)$', method)

class Request:
    req_id = None
    params = None
    srv_name = None
    method = None

    @classmethod
    def make(cls, req_id, srv_name, method, *params):
        assert req_id is not None
        full_method = srv_name + '::' + method
        return cls({
            'jsonrpc': '2.0',
            'id': req_id,
            'method': full_method,
            'params': params
        })

    def __init__(self, body):
        self.body = body
        self._parse_body(body)

    def clone(self):
        return Request(self.as_json())

    def is_notify(self):
        return self.req_id is None

    @property
    def full_method(self):
        return self.srv_name + '::' + self.method

    def as_json(self):
        data = {
            'jsonrpc': '2.0',
            'method': self.full_method,
            'params': self.params,
        }
        if self.req_id is not None:
            data['id'] = self.req_id
        return data

    def _parse_body(self, body):
        self.req_id = body.get('id')
        if not (self.req_id is None or
                isinstance(self.req_id, (str, int))):
            raise DataError('inval reqid')

        # parse params
        params = body.get('params', [])
        if not isinstance(params, (list, tuple, dict)):
            raise DataError('invalid params')
        self.params = params

        method = body['method']
        if not isinstance(method, str):
            raise DataError('invalid method')

        m = parse_method(method)
        if not m:
            raise DataError('invalid method')

        self.srv_name = m.group('srv')
        self.method = m.group('method')

    def error_response(self, error):
        assert error is not None
        return Response({
            'id': self.req_id,
            'error': error
            })

    def result(self, result):
        return Response({
            'id': self.req_id,
            'result': result
        })

    def allowed(self, whitelist):
        if not whitelist:
            return True
        return (self.full_method in whitelist or
                self.srv_name in whitelist)

class Response:
    error = None
    result = None
    req_id = None

    def __init__(self, body):
        self.body = body
        self._parse_body(body)

    def _parse_body(self, body):
        self.error = body.get('error')
        self.result = body.get('result')
        self.req_id = body.get('id')
        if self.req_id is None:
            raise DataError('req id is None')

        if not isinstance(self.req_id, (str, int)):
            raise DataError('invalid req_id')

    def as_json(self):
        data = {
            'jsonrpc': '2.0',
            'id': self.req_id,
            }
        if self.error is not None:
            data['error'] = self.error
        else:
            data['result'] = self.result
        return data
