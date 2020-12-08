from pytest import fixture
import app
from basicauth import decode, encode
import json


def test_something():
    assert 3 == 3


def test_index():
    assert {'hello': 'world'} == app.index()


@fixture
def api():
    from chalice.local import LocalGateway
    from chalice.config import Config
    return LocalGateway(app.app, Config())


def test_root_path(api):
    response = api.handle_request(method='GET', path='/', body=None, headers={})
    assert 200 == response['statusCode']
    assert {'hello': 'world'} == json.loads(response['body'])


def test_basic_authentication(api):
    autorization = {'Authorization': encode("edu", "edu")}
    response = api.handle_request(method='GET', path='/hello', body=None, headers=autorization)
    assert 200 == response['statusCode']

