#!/usr/bin/python3
#-------------------------------------------------------------------------------
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
#-------------------------------------------------------------------------------

import itertools
import collections
from time import time, sleep
from urllib.parse import urlparse
from platform import python_version as pyv
from copy import deepcopy

import requests

#from . import __version__ as cv
cv = '0.0.1'
from . import exceptions as exc
from .category import Category
from .file import File
from .page import Page
from .user import User
from .revision import Revision

#stackoverflow.com/questions/3217492/list-of-language-codes-in-yaml-or-json

__all__ = ["MediaWiki"]

#USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:14.0) Gecko/20100101 Firefox/14.0.1"
USER_AGENT = "Ceterach/%s (Python %s; mailto:riamse@protonmail.com)"
USER_AGENT %= cv, pyv()
def_config = {"throttle": 0,
              "retries": 1,
              "sleep": 5,
              "get": ('query', 'purge'),
              "defaults": {"maxlag": 5, "assert": "user"},
}


class MediaWiki:

#    def __init__(self, api_url="http://en.wikipedia.org/w/api.php", config=None):
#    def __init__(self, api_url="http://wiki.ciit.zp.ua/api.php", config=None): # 1.16
#    def __init__(self, api_url="http://wiki.mako.cc/api.php", config=None): # 1.19
    def __init__(self, api_url="http://test.wikipedia.org/w/api.php", config=None): # newest
    # def __init__(self, api_url="http://localhost:8080/srv/mediawiki/api.php", config=None): # 1.20
        """
        *api_url* is the full url to the wiki's API (default:
        ``"http://en.wikipedia.org/w/api.php"``).

        *config* is a dictionary whose keys are:

        - *throttle*, the number of seconds to wait in between
          requests (default: ``0``).
        - *retries*, how many times to retry after an error (default: ``1``).
          You can use ``float("inf")`` for an indefinite number of times.
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
        o = urlparse(api_url)
        if not o.path.endswith("api.php"):
            raise ValueError("Not an API url")
        api_url = (o.scheme or "http") + "://" + o.netloc + o.path
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
        """
        Returns a Category object for *identity*, which represents either a
        title or pageid.

        This method does not follow redirects, or check if the title is
        invalid. Those checks will be done when the Category's attributes are
        loaded.
        """
        params = {"follow_redirects": follow_redirects}
        params['pageid' if isinstance(identity, int) else 'title'] = identity
        return Category(self, **params)

    def file(self, identity, follow_redirects=False) -> File:
        """
        Returns a File object for *identity*, which represents either a
        title or pageid.

        This method does not follow redirects, or check if the title is
        invalid. Those checks will be done when the Category's attributes are
        loaded.
        """
        params = {"follow_redirects": follow_redirects}
        params['pageid' if isinstance(identity, int) else 'title'] = identity
        return File(self, **params)

    def page(self, identity, follow_redirects=False) -> Page:
        """
        Returns a Page object for *identity*, which represents either a
        title or pageid.

        This method does not follow redirects, or check if the title is
        invalid. Those will be done when the Page's attributes are loaded.
        """
        params = {"follow_redirects": follow_redirects}
        params['pageid' if isinstance(identity, int) else 'title'] = identity
        return Page(self, **params)

    def user(self, identity) -> User:
        """
        Returns a User object for *identity*, which represents the username.
        """
        return User(self, identity)

    def revision(self, identity) -> Revision:
        """
        Returns a Revision object for *identity*, which represents the revid.

        This method does not check if the revid is valid. That will be done
        when the Revision's attributes are loaded.
        """
        return Revision(self, identity)

    def call(self, params, use_defaults=True, **more_params):
        """
        Sends an API query to the wiki.
        *params* is a dict representing the query parameters.

        If *use_defaults* is True, the parameters specified in
        MediaWiki.config['defaults'] will be added to *params* if they are
        not already specified.

        If kwargs are specified in *more_params*, they will be used to update
        *params* before the request is sent.

        If the action is not specified it defaults to 'query'.

        Then, the 'format' key of *params* will be set to 'json'. In a word: ::

            if use_defaults:
                for k, v in defaults.items():
                    params.setdefault(k, v)
            for k, v in more_params.items(): params[k] = v
            params.setdefault("action", "query")
            params['format'] = 'json'

        If everything succeeded, the JSON data will be coerced to a Python
        object and returned.
        """
        time_since_last_query = time() - self.last_query
        conf = self.config
        throttle = conf['throttle']
        if time_since_last_query < throttle:
            sleep(throttle - time_since_last_query)
        if use_defaults:
            for (k, v) in conf['defaults'].items():
                params.setdefault(k, v)
        for (k, v) in more_params.items():
            params[k] = v
        params.setdefault("action", "query")
        params['format'] = 'json'
        for (k, v) in params.items():
            if isinstance(v, collections.Iterable) and not isinstance(v, str):
                params[k] = "|".join(str(i) for i in v)
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
                    retries = (int(conf['retries']),)
                except OverflowError:
                    retries = ()
                err = "Maximum number of retries reached ({0})"
                for _ in itertools.repeat(None, *retries):
                    sleep(conf['sleep'])
                    try:
                        res = urlopen(self.api_url, params=params)
                        ret = res.json()
                    except (requests.HTTPError, requests.ConnectionError) as e:
                        raiseme = exc.ApiError(e)
                    if not 'error' in ret:
                        break
                else:
                    raiseme = exc.ApiError(err.format(retries[0]))
            else:
                raiseme = exc.CeterachError(ret['error']['info'])
        if raiseme:
            if not 'error' in ret:
                code = 'py'
            else:
                code = ret["error"].get("code", "py")
            raiseme.code = code
            raise raiseme
        return ret

    def login(self, username, password):
        """
        Try to log the bot in.

        :type username: str
        :param username: Username to log in as.
        :type password: str
        :param password: Password that corresponds to the username.
        :returns: True if the login succeeded, False if not.
        """
        params = {"action": "login", "lgname": username, "lgpassword": password}
        result = self.call(use_defaults=False, **params)
        if result['login']['result'] == "Success":
            return True
        elif result['login']['result'] == "NeedToken":
            params['lgtoken'] = result['login']['token']
            result = self.call(use_defaults=False, **params)
            if result['login']['result'] == "Success":
                return True
        return False

    def logout(self):
        """
        Log the bot out.

        :returns: True
        """
        return self.call(action="logout", use_defaults=False) == []

    def set_token(self, *args):
        """
        Sets the Wiki's ``tokens`` attribute with the tokens specified in
        the *args*.

        If *args* are not specified, they will default to ``'edit'``.

        :param args: Strings that represent token names
        """
        allowed = set("block delete edit email import move "
                      "options patrol protect unblock watch".split())
        if not args:
            args = {"edit"}
        received = set(args)
        received = received & allowed
        query = {"action": "tokens", "type": received}
        try:
            res = self.call(**query)
        except exc.CeterachError:
            # The wiki does not support action=tokens
            query = {"prop": "info", "titles": "some random title",
                     "action": "query", "intoken": received}
            res = self.call(**query)['query']['pages']
            for prop, value in list(res.values())[0].items():
                if prop.endswith("token"):
                    self._tokens[prop[:-5]] = value
        else:
            # The wiki does support action=tokens
            for token_name, token_value in res['tokens'].items():
                self._tokens[token_name[:-5]] = token_value

    def expandtemplates(self, title, text, includecomments=False):
        """
        Evaluate the templates in *text* and return the processed result.

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
        :type includecomments: bool
        :param includecomments: Whether to include HTML comments in the output.
                                Defaults to False.
        :returns: Text with templates expanded.
        """
        params = {"action": "expandtemplates", "title": title, "text": text}
        if includecomments:
            params['includecomments'] = True
        return self.call(use_defaults=False, **params)['expandtemplates']["*"]

    def iterator(self, limit=float("inf"), **kwargs):
        """
        Iterates over an API query, so you no longer have to use something like: ::
            >>> res = api.call(action="query", ...)
            >>> blah(res["query"]["pages"][tuple(res["query"]["pages"].keys())[0]][...])

        :type limit: numbers.Real
        :param limit: The maximum number of items the iterator will yield.
                      Defaults to infinity.

        :returns: A generator that probably contains dicts.

        Example usage: ::

            >>> for s in api.iterator(list="allpages", apnamespace=0, aplimit=1, limit=3):
            ...     print(s)
            ...
            {'ns': 0, 'pageid': 5878274, 'title': '!'}
            {'ns': 0, 'pageid': 3632887, 'title': '!!'}
            {'ns': 0, 'pageid': 600744, 'title': '!!!'}

        """
        kwargs.pop("action", 0)
        l = 0
        while True:
            res = self.call(action='query', **kwargs)
            if isinstance(res['query'], list):
                return
            res['query'].pop("normalized", 0)
            res['query'].pop("redirects", 0)
            res['query'].pop("interwiki", 0)
            a_res = res['query'].values()
            if len(a_res) > 1:
                X = StopIteration # or maybe exc.ApiError?
                err = "Too many nodes under the query node: {0}"
                raise X(err.format(", ".join(res['query'].keys())))
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
            kwargs.update(c)

    @property
    def tokens(self):
        """A mapping of the token name to the token."""
        return deepcopy(self._tokens)

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
