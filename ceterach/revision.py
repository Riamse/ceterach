#!/usr/bin/python3
#-------------------------------------------------------------------------------
# This file is part of Ceterach.
# Copyright (C) 2013 Andrew Wang <andrewwang43@gmail.com>
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

import datetime

from . import exceptions as exc
from .utils import isostrptime, blah_decorate

def decorate(meth):
    msg = "Revision {0!r} does not exist"
    attr = 'revid'
    err = exc.NonexistentRevisionError
    return blah_decorate(meth, msg, attr, err)

class Revision:

    def __init__(self, api, revid):
        self._api = api
        self._revid = revid

    def __eq__(self, other):
        return other._api == self._api and self.revid == self.revid

    def __ne__(self, other):
        return other._api != self._api or self.revid != self.revid

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
        self._summary = res['comment']
        self._timestamp = isostrptime(res['timestamp'])
        self._user = self._api.user(res['user'])
        self._is_minor = 'minor' in res
        try:
            self._rvtoken = res['rollbacktoken']
        except KeyError:
            pass
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
        """
        Replace the page's content with the content found in this revision.
        *summary* is the edit summary used for the edit. The edit will be
        marked as minor if *minor* is True, and if *bot* is True and the
        logged-in user has the bot flag, it will also be marked as a bot
        edit.

        Set *force* to True in order to make the edit in spite of edit
        conflicts and nonexistence.

        :type summary: str
        :param summary: The comment to use for the modification, also known as
                        the edit summary.
        :type minor: bool
        :param minor: Mark the edit as minor, if set to True.
        :type bot: bool
        :param bot: Mark the edit as a bot edit, if the logged in user has the
                    bot flag and the parameter is set to True.
        :type force: bool
        :param force: If set to True, ignore edit conflicts and create the
                      page if it doesn't already exist.
        :returns: A dictionary containing the API query result.
        """
        return self.page.edit(self.content, summary, minor, bot, force)

    def rollback(self, summary="", bot=False):
        params = {"title": self.page._api, "user": self.user.name,
                  "token": self.rvtoken, "action": "rollback"
        }
        try:
            params['token'] = self.rvtoken
        except AttributeError:
            err = "You do not have the rollback permission"
            raise exc.PermissionError(err)
        if summary is not None:
            params['summary'] = summary
        if bot:
            params['markbot'] = 1
        return self._api.call(**params)

#    def delete(self):
#        pass
#
#    def undelete(self):
#        pass

    @property
    @decorate
    def revid(self) -> int:
        return "_revid"

    @property
    @decorate
    def rvtoken(self) -> str:
        return "_rvtoken"

    @property
    @decorate
    def page(self):
        #: :type: ceterach.page.Page
        attr = "_page"
        return attr

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
    def user(self):
        #: :type: ceterach.user.User
        attr = "_user"
        return attr

    @property
    @decorate
    def is_minor(self) -> bool:
        return "_is_minor"

    @property
    @decorate
    def prev_revision(self):
        #: :type: ceterach.revision.Revision
        attr = "_prev_revision"
        return attr

    @property
    @decorate
    def content(self) -> str:
        return "_content"

    @property
    @decorate
    def is_deleted(self) -> bool:
        return "_is_deleted"
