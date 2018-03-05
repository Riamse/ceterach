import pytest
import requests_mock
from decorator import decorator as dec

import ceterach as c

# Mock MediaWiki API URL
WIKI_BASE = 'mock://a.wiki/w/api.php'
TEST_TOKEN = 'abcdefghijklmnopqrstuvwxyz1hunter2345678+\\'
TEST_PAGE = 'Noodling'
TEST_USER = 'Hamilton'


def q(val):
    """Wraps fake response data."""
    return {'query': val}


def _test_for(responses, num_called=1):
    """Boilerplate decorator that sets up mock requests."""

    if type(responses) is dict:
        responses = [responses]

    for i, r in enumerate(responses):
        responses[i] = {'json': r}

    def decorator(inner):
        def decorator_inner(f, *args, **kwargs):
            with requests_mock.mock() as rqm:
                rqm.register_uri(requests_mock.ANY, WIKI_BASE, responses)
                f(*args, **kwargs)
            assert rqm.call_count == num_called

        return dec(decorator_inner, inner)

    return decorator


@pytest.fixture
def api():
    return c.api.MediaWiki(WIKI_BASE)


def test_repr(api):
    assert repr(api).startswith('MediaWiki(api_url=\'' + WIKI_BASE)


def test_eq(api):
    assert api == c.api.MediaWiki(WIKI_BASE)
    assert api != c.api.MediaWiki(reversed(WIKI_BASE))


@pytest.mark.parametrize('t', [
    c.page.Page,
    c.category.Category,
    c.file.File,
])
def test_page_types(api, t):
    type_name = t.__name__
    name = '{}:{}'.format(type_name, TEST_PAGE)
    api_func = getattr(api, type_name.lower())

    obj = api_func(name)
    assert obj.title == name
    assert type(obj) == t


def test_user(api):
    user = api.user(TEST_USER)
    assert user.name == TEST_USER
    assert type(user) == c.user.User


def test_revision(api):
    rev = api.revision(1)
    assert rev.revid == 1
    assert type(rev) == c.revision.Revision


@_test_for({'tokens': {'edittoken': TEST_TOKEN}})
def test_tokens_action_tokens(api):
    api.set_token()
    assert ('edit', TEST_TOKEN) in api.tokens.items()


@_test_for({'tokens': {'csrftoken': TEST_TOKEN, 'emailtoken': TEST_TOKEN}})
def test_tokens_action_tokens_multiple(api):
    api.set_token('csrf', 'email')
    assert ('csrf', TEST_TOKEN) in api.tokens.items()
    assert ('email', TEST_TOKEN) in api.tokens.items()


@_test_for([
    {'error': {
        'code': 'unknown_action',
        'info': 'Unrecognized value for parameter \'action\': '
                'tokens'
    }},
    q({'pages': {
        '-1': {
            'edittoken': TEST_TOKEN
        }
    }})
], 2)
def test_tokens_action_query(api):
    api.set_token()
    assert ('edit', TEST_TOKEN) in api.tokens.items()


@_test_for(q({'namespaces': [{'id': 0,
                              'case': 'first-letter',
                              'content': '',
                              '*': ''},
                             {'id': 1337,
                              'case': 'first-letter',
                              'canonical': 'Spam',
                              '*': 'Spam'}]}))
def test_namespaces(api):
    ns = api.namespaces
    assert len(ns) == 2
    assert ns[1337] == 'Spam'


@_test_for({})
def test_logout(api):
    assert api.logout()
