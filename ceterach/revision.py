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

import functools
import datetime

from . import exceptions as exc
from .utils import isostrptime
# TODO: Deal with decorator code redundancy
def decorate(meth):
    attr = meth(0) # The method should be returning the attribute to get
    @functools.wraps(meth)
    def wrapped(self):
        if not hasattr(self, attr): self.load_attributes()
        try:
            return getattr(self, attr)
        except AttributeError:
            err = "Revision {0!r} does not exist".format(self.revid)
        raise exc.NonexistentRevisionError(err)
    return wrapped

class Revision:

    def __init__(self, api, revid):
        self._api = api
        self._revid = revid

    def load_attributes(self, res=None):
        self.__load(res)

    def __load(self, res):
        i = self._api.iterator
        rvprop = ('ids', 'flags', 'timestamp', 'user', 'comment', 'content')
        kwargs = {"revids": self._revid,
                  "prop": "revisions",
                  "rvprop": rvprop,
                  "rvtoken": "rollback"
        }
        res = res or list(i(1, **kwargs))[0]
        self._page = self._api.page(res['pageid'])
        res = res['revisions'][0]
        self._rvtoken = res['rollbacktoken']
        self._summary = res['comment']
        self._timestamp = isostrptime(res['timestamp'])
        self._user = self._api.user(res['user'])
        self._is_minor = 'minor' in res
        if res['parentid']:
            self._prev_revision = Revision(self._api, res['parentid'])
        else:
            self._prev_revision = None
        try:
            self._content = res["*"]
        except KeyError:
            self._is_deleted = True
#            self._is_deleted = 'texthidden' in res
        else:
            self._is_deleted = False

    def restore(self, summary="", minor=False, bot=True, force=False):
        pass

    def rollback(self, summary="", bot=False):
        params = {"title": self.page.title, "user": self.user.name,
                  "token": self._rvtoken, "action": "rollback"
        }
        if summary is not None:
            params['summary'] = summary
        if bot:
            params['markbot'] = 1
        return self._api.call(**params)

    def delete(self):
        pass

    def undelete(self):
        pass

    @property
    @decorate
    def page(self) -> object:
        return "_page"

    @property
    @decorate
    def summary(self) -> str:
        return "_summary"

    @property
    @decorate
    def timestamp(self)-> datetime.datetime:
        return "_timestamp"

    @property
    @decorate
    def user(self) -> object:
        return "_user"

    @property
    @decorate
    def is_minor(self) -> bool:
        return "_is_minor"

    @property
    @decorate
    def prev_revision(self) -> object:
        return "_prev_revision"

    @property
    @decorate
    def content(self) -> str:
        return "_content"

    @property
    @decorate
    def is_deleted(self) -> bool:
        return "_is_deleted"
