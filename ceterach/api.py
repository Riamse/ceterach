#!/usr/bin/python3
# -----------------------------------------------------------------------------
# This file is part of Ceterach.
# Copyright (C) 2013 Riamse <riamse@protonmail.com>
#
# Ceterach is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# Ceterach is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Ceterach.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

import itertools
import collections
from time import time, sleep
from urllib.parse import urlparse
from platform import python_version as pyv
from copy import deepcopy

import requests

# from . import __version__ as cv
cv = '0.0.1'
from . import exceptions as exc
from .category import Category
from .file import File
from .page import Page
from .user import User
from .revision import Revision

# stackoverflow.com/questions/3217492/list-of-language-codes-in-yaml-or-json

__all__ = ["MediaWiki"]

# USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:14.0) Gecko/20100101 Firefox/14.0.1"
USER_AGENT = "Ceterach/%s (Python %s; mailto:riamse@protonmail.com)"
USER_AGENT %= cv, pyv()
def_config = {"throttle": 0,
              "retries": 1,
              "sleep": 5,
              "get": ('query', 'purge'),
              "defaults": {"maxlag": 5, "assert": "user"}
}


class MediaWiki:
    def __init__(self, api_url="http://en.wikipedia.org/w/api.php", config=None):
#    def __init__(self, api_url="http://wiki.ciit.zp.ua/api.php", config=None): # 1.16
#    def __init__(self, api_url="http://wiki.mako.cc/api.php", config=None): # 1.19
#    def __init__(self, api_url="http://test.wikipedia.org/w/api.php", config=None): # newest
#    def __init__(self, api_url="http://localhost:8080/srv/mediawiki/api.php", config=None): # 1.20
        """*api_url* is the full url to the wiki's API (default:
        ``"http://en.wikipedia.org/w/api.php"``).

        *config* is a dictionary whose keys are:

        - *throttle*, the number of seconds to wait in between
          requests (default: ``0``).
        - *retries*, how many times to retry after an error (default: ``1``).
          You can use ``float("inf")`` to keep retrying until it works.
        - *sleep*, the number of seconds to sleep between each retry after an
          error (default: ``5``).
        - *get*, a tuple of which modules can accept GET requests, which
          can vary from wiki to wiki (default: ``("query", "purge")``).
        - *defaults*, a dict that comprises additional parameters to be sent
          with each request. These can be overwritten on an individual basis
          by explicitly specifying the parameter in ``MediaWiki.call``
          (default: ``{"maxlag": 5, "assert": "user"}``.

          The default parameters are:
                   - *maxlag*, the maximum number of seconds the wiki's slave
                     servers are allowed to lag until stopping the
                     request (default: ``5``). For more information, see
                     `MediaWiki
                     docs <http://www.mediawiki.org/wiki/Manual:Maxlag>`_\.
                   - *assert*, used according to the (former) MediaWiki
                     extension (default: ``'user'``). For more information,
                     refer to `the
                     docs <https://www.mediawiki.org/wiki/API:Assert>`_\.

        *config* can also be a dictionary that only contains those parameters
        you wish to modify. Passing ``{"throttle": 3.14}``, for example, will
        result in a dictionary with the above parameters, except the throttle
        will be 3.14.
        """
        self._tokens = {}
        self._namespaces = None
        self.api_url = api_url
        self.config = deepcopy(def_config)
        self.config.update(config or {})
        self.last_query = time()
        self.opener = requests.Session()
        self.opener.headers.update({"User-Agent": USER_AGENT})

    def __repr__(self):
        cls_name = type(self).__name__
        text = "{c}(api_url={self.api_url!r}, config={self.config!r})"
        return text.format(c=cls_name, self=self)

    def __eq__(self, other):
        return getattr(other, 'api_url', None) == self.api_url

    def __ne__(self, other):
        return getattr(other, 'api_url', None) != self.api_url

    def category(self, identity, follow_redirects=False) -> Category:
        """Returns a Category object for *identity*, which represents either a
        title or pageid.

        This method does not follow redirects, or check if the title is
        invalid. Those checks will be done when the Category's attributes are
        loaded.
        """
        params = {
            "follow_redirects": follow_redirects,
            'pageid' if isinstance(identity, int) else 'title': identity
        }
        return Category(self, **params)

    def file(self, identity, follow_redirects=False) -> File:
        """Returns a File object for *identity*, which represents either a
        title or pageid.

        This method does not follow redirects, or check if the title is
        invalid. Those checks will be done when the Category's attributes are
        loaded.
        """
        params = {
            "follow_redirects": follow_redirects,
            'pageid' if isinstance(identity, int) else 'title': identity
        }
        return File(self, **params)

    def page(self, identity, follow_redirects=False) -> Page:
        """Returns a Page object for *identity*, which represents either a
        title or pageid.

        This method does not follow redirects, or check if the title is
        invalid. Those will be done when the Page's attributes are loaded.
        """
        params = {
            "follow_redirects": follow_redirects,
            'pageid' if isinstance(identity, int) else 'title': identity
        }
        return Page(self, **params)

    def user(self, identity) -> User:
        """
        Returns a User object for *identity*, which represents the username.
        """
        return User(self, identity)

    def revision(self, identity) -> Revision:
        """Returns a Revision object for *identity*, which represents the revid.

        This method does not check if the revid is valid. That will be done
        when the Revision's attributes are loaded.
        """
        return Revision(self, identity)

    def _call(self, params, more_params=None, use_defaults=False):
        time_since_last_query = time() - self.last_query
        conf = self.config
        throttle = conf['throttle']
        if throttle and time_since_last_query < throttle:
            sleep(throttle - time_since_last_query)
        params = self._build_call_params(params, more_params, use_defaults)
        is_get = params['action'] in conf['get']
        raiseme = None
        urlopen = getattr(self.opener, 'get' if is_get else 'post')
        try:
            res = urlopen(self.api_url, **{"params" if is_get else "data": params})
        except (requests.HTTPError, requests.ConnectionError) as e:
            # We need something that can be arbitrarily assigned attributes
            res = lambda: 0
            res.json = lambda: {}
            raiseme = exc.ApiError(e)
        self.last_query = time()
        try:
            ret = res.json()
        except ValueError:
            ret = {"error": {"code": "py", "info": "No JSON object could be decoded"}}
        if 'error' in ret:
            if ret['error']['code'] == 'maxlag':
                try:
                    retries = int(conf['retries']),
                except OverflowError:
                    retries = ()
                err = "Maximum number of retries reached ({0})"
                for _ in itertools.repeat(None, *retries):
                    sleep(conf['sleep'])
                    try:
                        res = urlopen(self.api_url, **{"params" if is_get else "data": params})
                        ret = res.json()
                    except (requests.HTTPError, requests.ConnectionError) as e:
                        raiseme = exc.ApiError(e)
                    if 'error' not in ret:
                        break
                else:
                    raiseme = exc.ApiError(err.format(retries[0]))
            else:
                raiseme = exc.CeterachError(ret['error']['info'])
        if raiseme:
            if 'error' not in ret:
                code = 'py'
            else:
                code = ret["error"].get("code", "py")
                raiseme.response = ret
            raiseme.code = code
            raise raiseme
        return ret

    def _build_call_params(self, params, more_params, use_defaults):
        final_dict = {}
        for (k, v) in params.items():
            final_dict[k] = v
        if use_defaults:
            for (k, v) in self.config['defaults'].items():
                final_dict.setdefault(k, v)
        if more_params:
            for (k, v) in more_params.items():
                final_dict[k] = v
        for (k, v) in final_dict.items():
            if isinstance(v, (list, tuple, set)):
                final_dict[k] = "|".join(str(i) for i in v)
        final_dict.setdefault("action", "query")
        final_dict['format'] = 'json'
        return final_dict

    def call(self, params=None, **more_params):
        """Sends an API query to the wiki.
        *params* is a dict representing the query parameters.

        If the *use_defaults* parameter (accepted only as a kwarg) is True,
        the parameters specified in MediaWiki.config['defaults'] will be
        added to *params* if they are not already specified.

        Next, if *more_params* is specified, it will be used to update
        *params*.

        If the same key appears in *params*, Mediawiki.config['defaults'],
        and *more_params*, then the keys of *more_params* take precedence
        over the keys of *params* and the keys of *params* take precedence
        over the keys of Mediawiki.config['defaults'].

        If the action is not specified it defaults to 'query'. The format
        key will be set to 'json'.

        To illustrate this, suppose that ``api = MediaWiki()`` and
        ``api.config["defaults"] = {"default": 1}``. The call method, given
        these arguments, will send the dict in the comment to the API::

            api.call({"p": 1}) # p=1, format='json', action='query', default=1
            api.call({"action": "edit", "p": 1}) # p=1, format='json', action='edit', default=1
            api.call({"p": 1}, use_defaults=False) # p=1, action='query', format='json'
            api.call({"p": 1, 'default': 0}) # p=1, format='json', action='query', default=0
            api.call({"p": 1}, default=100) # p=1, format='json', action='query', default=100
            api.call({"p": 1, 'default': 0}, default=1000) # p=1, format='json', action='query', default=1000

        If everything succeeded, we return the JSON data.
        """
        if not params:
            params = {}
        use_defaults = more_params.pop("use_defaults", True)
        return self._call(params, more_params, use_defaults=use_defaults)

    def login(self, username, password):
        """Try to log in with the given username and password.

        :type username: str
        :param username: Username to log in as.
        :type password: str
        :param password: Password that corresponds to the username.
        :returns: True if the login succeeded, False if not.
        """
        params = {"action": "login", "lgname": username, "lgpassword": password}
        result = self.call(params, use_defaults=False)
        if result['login']['result'] == "Success":
            return True
        elif result['login']['result'] == "NeedToken":
            params['lgtoken'] = result['login']['token']
            result = self.call(params, use_defaults=False)
            if result['login']['result'] == "Success":
                return True
        return False

    def logout(self):
        """Log the bot out.

        :returns: True
        """
        return len(self.call(action="logout", use_defaults=False)) == 0

    def set_token(self, *args):
        """Sets the Wiki's ``tokens`` attribute with the tokens specified in
        the *args*.

        If *args* are not specified, they will default to ``'edit'``.

        :param args: Strings that represent token names
        """
        if not args:
            args = {"edit"}
        received = set(args)
        query = {"action": "tokens", "type": received}
        try:
            res = self.call(query)
        except exc.CeterachError:
            # The wiki does not support action=tokens
            query = {
                "prop": "info", "titles": "some random title",
                "action": "query", "intoken": received
            }
            res = self.call(query)['query']['pages']
            for prop, value in list(res.values())[0].items():
                if prop.endswith("token"):
                    self._tokens[prop[:-5]] = value
        else:
            # The wiki does support action=tokens
            for token_name, token_value in res['tokens'].items():
                self._tokens[token_name[:-5]] = token_value

    def expand_templates(self, title, text, include_comments=False) -> str:
        """Evaluate the templates in *text* and return the processed result.

        For more information, see `MediaWiki docs <http://www.mediawiki.org/wi
        ki/API:Parsing_wikitext#expandtemplates>`_.

        :type title: str
        :param title: Act like the wikicode is on this page (default:
                      ``"API"``).
                      This only really matters when parsing links to the page
                      itself or links to subpages, or when using `magic words
                      <http://www.mediawiki.org/wiki/Help:Magic_words>`_ like
                      {{PAGENAME}}.
        :type text: str
        :param text: Wikicode to process.
        :type include_comments: bool
        :param include_comments: Whether to include HTML comments in the output.
                                Defaults to False.
        :returns: Text with templates expanded.
        """
        params = {"action": "expandtemplates", "title": title, "text": text}
        if include_comments:
            params['includecomments'] = True
        return self.call(params, use_defaults=False)['expandtemplates']["*"]

    def olditerator(self, params=None, limit=float("inf"), **more_params):
        """Iterates over an API query, so you no longer have to use something like: ::
            >>> res = api.call(action="query", ...)
            >>> res["query"]["pages"][tuple(res["query"]["pages"].keys())[0]][...]

        :type params: dict
        :param params: Parameters to the query.
        :type limit: numbers.Real
        :param limit: The maximum number of items the iterator will yield.
                      Defaults to infinity.
        :param more_params: Parameters to the query, which will be added to
                            *params*. See .call() for similar behaviour.

        :returns: A generator that probably contains dicts.

        Example usage: ::

            >>> for s in api.iterator(list="allpages", apnamespace=0, aplimit=1, limit=3):
            ...     print(s)
            ...
            {'ns': 0, 'pageid': 5878274, 'title': '!'}
            {'ns': 0, 'pageid': 3632887, 'title': '!!'}
            {'ns': 0, 'pageid': 600744, 'title': '!!!'}

        """
        if not params:
            params = {}
        params = params.copy()
        l = 0
        while True:
            res = self.call(params, rawcontinue='', **more_params)
            # print("QUERY")
            if isinstance(res['query'], list):
                return
            res['query'].pop("normalized", 0)
            res['query'].pop("redirects", 0)
            res['query'].pop("interwiki", 0)
            a_res = res['query'].values()
            if len(a_res) > 1:
                # eg if you specify both a list= and prop=
                X = ValueError
                err = "Too many nodes under the query node: "
                raise X(err + ", ".join(res['query'].keys()))
            else:
                ret = list(a_res)[0]
                if isinstance(ret, dict):
                    ret = list(ret.values())
            for r in ret:
                yield r
                l += 1
                if l >= limit:
                    return
            if 'query-continue' in res:
                c, p = {}, {}
                for p_, n in res['query-continue'].items():
                    for k, v in n.items():
                        c[k] = v
                        p[p_] = 1  # what is this even doing here
            else:
                return
            params.update(c)

    def newiterator(self, params=None, limit=float("inf"), **more_params):
        """Iterates over an API query, so you no longer have to use something like: ::
            >>> res = api.call(action="query", ...)
            >>> res["query"]["pages"][tuple(res["query"]["pages"].keys())[0]][...]

        :type params: dict
        :param params: Parameters to the query.
        :type limit: numbers.Real
        :param limit: The maximum number of items the iterator will yield.
                      Defaults to infinity.
        :param more_params: Parameters to the query, which will be added to
                            *params*. See .call() for similar behaviour.

        :returns: A generator that probably contains dicts.

        Example usage: ::

            >>> for s in api.iterator(list="allpages", apnamespace=0, aplimit=1, limit=3):
            ...     print(s)
            ...
            {'ns': 0, 'pageid': 5878274, 'title': '!'}
            {'ns': 0, 'pageid': 3632887, 'title': '!!'}
            {'ns': 0, 'pageid': 600744, 'title': '!!!'}

        """
        if not params:
            params = {}
        params = params.copy()
        l = 0
        while True:
            res = self.call(params, **more_params)
            if isinstance(res['query'], list):
                return
            res['query'].pop("normalized", 0)
            res['query'].pop("redirects", 0)
            res['query'].pop("interwiki", 0)
            a_res = res['query'].values()
            if len(a_res) > 1:
                # eg if you specify both a list= and prop=
                X = ValueError
                err = "Too many nodes under the query node: "
                raise X(err + ", ".join(res['query'].keys()))
            else:
                ret = list(a_res)[0]
                if isinstance(ret, dict):
                    ret = list(ret.values())
            for r in ret:
                yield r
                l += 1
                if l >= limit:
                    return
            if 'continue' in res:
                c = res['continue']  # easy stuff now
            else:
                return
            params.update(c)

    iterator = olditerator

    @property
    def tokens(self):
        """A mapping of the token name to the token."""
        return self._tokens

    @property
    def namespaces(self):
        """A mapping of the namespace number to the namespace name."""
        if self._namespaces is None:
            self._namespaces = {}
            for ns in self.iterator(use_defaults=False,
                                    meta="siteinfo", siprop="namespaces"):
                nsid = ns['id']
                self._namespaces[nsid] = ns["*"]
        return self._namespaces
