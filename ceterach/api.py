#!/usr/bin/python3
#-------------------------------------------------------------------------------
# This file is part of Ceterach.
# Copyright (C) 2012 Riamse <riamse@protonmail.com>
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

from . import exceptions as exc
from .category import Category
from .file import File
from .page import Page
from .user import User
from .utils import flattened, DictThatReturnsNoneInsteadOfRaisingKeyError

#stackoverflow.com/questions/3217492/list-of-language-codes-in-yaml-or-json

__all__ = ["MediaWiki"]

USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:14.0) Gecko/20100101 Firefox/14.0.1"
#USER_AGENT = "Ceterach/{0!s} (Python {1!s}; mailto:riamse@protonmail.com)"
#USER_AGENT = USER_AGENT.format(cv, pyv())
USER_AGENT.format(pyv())
def_config = {"throttle": 0,
              "maxlag": 5,
              "retries": 0,
              "get": ('query', 'purge'),
}

class MediaWiki:

    _tokens = DictThatReturnsNoneInsteadOfRaisingKeyError()
    _namespaces = None

    def __init__(self, api_url="http://en.wikipedia.org/w/api.php", config=None):
#    def __init__(self, api_url="http://wiki.ciit.zp.ua/api.php", config=None): # 1.16
#    def __init__(self, api_url="http://wiki.mako.cc/api.php", config=None): # 1.19
        """
        *api_url* is the full url to the wiki's API (default:
        ``"http://en.wikipedia.org/w/api.php"``).

        *config* is a dictionary whose keys are:

        - *throttle*, the number of seconds to wait in between
          requests (default: ``0``).
        - *maxlag*, the maximum number of seconds the wiki's slave
          servers are allowed to lag until stopping the
          request (default: ``5``). For more information, see `MediaWiki
          docs <http://www.mediawiki.org/wiki/Manual:Maxlag>`_\.
        - *retries*, how many times to retry after an error (default: ``0``).
          You can use ``float("inf")`` for an indefinite number of times.
        - *get*, a tuple of which modules can accept GET requests, which
          can vary from wiki to wiki (default: ``("query", "purge")``).
        """
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
        text = "{c}(api_url={api!r}, config={conf!r})"
        return text.format(c=cls_name, api=self.api_url, conf=self.config)

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

    def call(self, **params) -> type("", (collections.UserDict, list), {}):
        # Annotated so the IDE will autocomplete convenient methods.
        # it may be true that true, false, and null are valid Python objects,
        # but those don't have any methods worth autocompleting.
        """
        Sends an API query to the wiki, with *params* as query parameters.
        Before the request is sent, the 'format' key of *params* will be set
        to 'json'.

        If everything succeeded, the JSON data will be coerced to a Python
        object and returned.
        """
        conf = self.config
        time_since_last_query = time() - self.last_query
        throttle = conf['throttle']
        if time_since_last_query < throttle:
            sleep(throttle - time_since_last_query)
        params.setdefault("maxlag", conf['maxlag'])
        params.setdefault("action", "query")
        params.update({"format": "json"})
        for (k, v) in params.items():
            if isinstance(v, collections.Iterable) and not isinstance(v, str):
                v = flattened(v)
                params[k] = "|".join(str(i) for i in v)
        is_get_action = params['action'] in conf['get']
        urlopen = getattr(self.opener, 'get' if is_get_action else 'post')
        del is_get_action
        try:
            res = urlopen(self.api_url, params=params)
        except (requests.HTTPError, requests.ConnectionError):
            raise exc.ApiError("REQUEST FAILURE.")
        self.last_query = time()
        ret = res.json() # If it fails, it'll raise a ValueError
        if 'error' in ret:
            if ret['error']['code'] == 'maxlag':
                try:
                    retries = (int(conf['retries']),)
                except OverflowError:
                    retries = ()
                err = "Maximum number of retries reached {0}"
                for _ in itertools.repeat(None, *retries):
                    sleep(throttle)
                    try:
                        res = urlopen(self.api_url, params=params)
                        ret = res.json()
                    except (requests.HTTPError, requests.ConnectionError):
                        raise exc.ApiError("REQUEST FAILURE.")
                    if not 'error' in ret:
                        break
                else:
                    raise exc.ApiError(err.format(retries))
            else:
                raise ValueError(ret['error']['info'])
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
        result = self.call(**params)
        if result['login']['result'] == "Success":
            return True
        elif result['login']['result'] == "NeedToken":
            params['lgtoken'] = result['login']['token']
            result = self.call(**params)
            if result['login']['result'] == "Success":
                return True
        return False

    def logout(self):
        """
        Log the bot out.

        :returns: True
        """
        return self.call(action="logout") == []

    def set_token(self, *args):
        """
        Sets the Wiki's ``tokens`` attribute with the tokens specified in
        the *args*.

        If *args* are not specified, they will default to ``'delete', 'block',
        'patrol', 'protect', 'unblock', 'options', 'email', 'edit', 'import',
        'move', 'watch'``. This
        method will work only if a user is logged in.

        :param args: Strings that represent token names
        """
        allowed = set("block delete edit email import move "
                      "options patrol protect unblock watch".split())
        if not args:
            args = allowed
        received = set(args)
        invalid_args = received - allowed
        for bad_token in invalid_args:
            received.remove(bad_token)
        query = {"action": "tokens", "type": received}
        try:
            res = self.call(**query)
        except exc.ApiError:
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
        return self.call(**params)['expandtemplates']["*"]

    def iterator(self, limit=float("inf"), **kwargs):
        """
        Iterates over an API query.
        The contents are usually dicts that represent a page.

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
                        p[p_] = 1
            else:
                return
            kwargs.update(c)

    def purge(self, **kwargs):
        """
        Takes *kwargs* and purges them.

        This implements the iterator method, so in order to actually purge
        the pages, it iterates over the generator by returning a tuple.

        A dict within the tuple will contain the 'purged' key if the page
        was successfully purged.

        :param kwargs: The single keyword must be 'titles', 'pageids', or
         'revids'. The value must be a list of pages to purge, representing
         page titles, page ids, or revision ids.
        :returns: A tuple of dicts.
        """
        allowed = {"titles", "pageids", "revids"}
        if len(kwargs) > 1:
            err = "Cannot supply multiple sources of pages to purge"
            raise TypeError(err)
        elif tuple(kwargs)[0] not in allowed:
            err = "Invalid parameter {0!r}; keyword must be in {1!r}"
            raise ValueError(err.format(tuple(kwargs)[0], allowed))
        return tuple(self.iterator(action='purge', **kwargs))

    @property
    def tokens(self):
        return deepcopy(self._tokens)

    @property
    def namespaces(self):
        if self._namespaces is None:
            self._namespaces = {}
            for ns in self.iterator(meta="siteinfo", siprop="namespaces"):
                nsid = ns['id']
                self._namespaces[nsid] = ns["*"]
        return self._namespaces
