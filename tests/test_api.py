from unittest import TestCase
from unittest.mock import patch

import requests_mock

from ceterach import api

# Mock MediaWiki API URL
WIKI_BASE = 'mock://a.wiki/w/api.php'

TEST_TOKEN = 'abcdefghijklmnopqrstuvwxyz1hunter2345678+\\'


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
        def decorator_inner(*args):
            with requests_mock.mock() as rqm:
                rqm.register_uri(requests_mock.ANY, WIKI_BASE, responses)
                inner(*args)
            assert rqm.call_count == num_called

        return decorator_inner

    return decorator


class TestMediaWiki(TestCase):
    def setup_class(self):
        self.api = api.MediaWiki(WIKI_BASE)

    @_test_for({'tokens': {'csrftoken': TEST_TOKEN}})
    def test_tokens_action_tokens(self):
        self.api.set_token()
        assert ('csrf', TEST_TOKEN) in self.api.tokens.items()

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
    def test_tokens_action_query(self):
        self.api.set_token()
        assert ('edit', TEST_TOKEN) in self.api.tokens.items()

    @_test_for(q({'namespaces': [{'id': 0,
                                      'case': 'first-letter',
                                      'content': '',
                                      '*': ''},
                                 {'id': 1337,
                                      'case': 'first-letter',
                                      'canonical': 'Spam',
                                      '*': 'Spam'}]}))
    def test_namespaces(self):
        ns = self.api.namespaces
        assert len(ns) == 2
        assert ns[1337] == 'Spam'

    @_test_for({})
    def test_logout(self):
        assert self.api.logout()
