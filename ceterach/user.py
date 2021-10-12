#!/usr/bin/python3
# ------------------------------------------------------------------------------
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
# ------------------------------------------------------------------------------

from datetime import datetime
try:
    from ipaddress import ip_address
except ImportError:
    # The ipaddress module is included on a provisional basis.
    # In case it ever gets removed, we can use a regex hack to check
    # if a user is an IP address or not.
    #
    # Also, this provides support for Python 3.2
    from .utils import ip_address
from . import exceptions as exc
from .utils import isostrptime, blah_decorate

__all__ = ['User']


def decorate(meth):
    msg = "User {0!r} does not exist"
    attr = "name"
    err = exc.NonexistentUserError
    return blah_decorate(meth, msg, attr, err)


class User:
    def __init__(self, api, name):
        self._api = api
        self._name = name

    def __repr__(self):
        cls_name = type(self).__name__
        text = "{c}(api={self._api!r}, name={self.name!r})"
        return text.format(c=cls_name, self=self)

    def __eq__(self, other):
        return getattr(other, '_api', None) == self._api and \
               getattr(other, 'name', None) == self.name

    def __ne__(self, other):
        return getattr(other, '_api', None) != self._api or \
               getattr(other, 'name', None) != self.name

    def load_attributes(self, res=None):
        """Call this to load ``self.__title``, ``._is_redirect``, ``._pageid``,
        ``._exists``, ``._namespace``, ``._creator``, and ``._revid``.

        This method also resolves redirects if ``follow_redirects=True`` was
        passed to the constructor. If the page is a redirect, the method will
        make a grand total of 2 API queries.

        If the *res* parameter was supplied, the method will pretend that
        was what the first query returned. As such, if redirects are followed,
        a single API query will be made.

        :type res: dict
        :param res: The result of an earlier API request (optional). If you
                    are planning to set this parameter to a
                    value other than None, the minimal API request parameters
                    needed for this method to function
                    correctly are: ``{'usprop': ('blockinfo', 'groups',
                    'rights', 'editcount', 'registration', 'emailable',
                    'gender'), 'list': 'users'}``
        """
        self._is_ip = False
        try:
            self._is_ip = bool(ip_address(self.name))
        except ValueError:
            pass
        props = (
            "blockinfo", "groups", "rights", "editcount",
            "registration", "emailable", "gender",
        )
        res = res or self._api.call(use_defaults=False,
                                    action="query", list="users",
                                    ususers=self._name,
                                    usprop=props)['query']['users'][0]
        # normalize our username in case it was entered oddly
        self._name = res['name']
        self._userpage = self._api.page("User:" + self.name)
        if 'missing' in res:
            self._exists = False
            return
        else:
            self._exists = True
        ## The following checks are for sites that run ancient MediaWiki ##
        self._userid = res.get("userid", 0)
        self._gender = res.get("gender", "unknown")
        try:
            self._rights = tuple(res['rights'].values())
        except KeyError:
            self._rights = ()
        except AttributeError:
            # MediaWiki does weird stuff, sometimes returning a list or
            # a dict with numbers as keys...
            self._rights = tuple(res['rights'])
        ## End ancient MediaWiki checks ##
        try:
            self._blockinfo = {
                "by": res['blockedby'],
                "reason": res['blockreason'],
                "expiry": res['blockexpiry'],
            }
        except KeyError:
            self._blockinfo = {"by": None, "reason": None, "expiry": None}
        self._groups = tuple(res.get("groups", ""))
        self._editcount = res.get("editcount", 0)
        reg = res.get("registration", None)  # For IP addresses
        try:
            self._registration = isostrptime(reg)
        except TypeError:
            # Sometimes the API doesn't give a date; the user's probably really
            # old. There's nothing else we can do!
            self._registration = datetime.min
        self._emailable = 'emailable' in res

    def email(self, subject, text, cc=True):
        """Send an email to the user.

        :type subject: str
        :param subject: sSubject of the email
        :type text: str
        :param text: (plain text) content of the email.
        :type cc: bool
        :param cc: Whether you wish to send yourself a copy of the email.
        :returns: The result of the API query.
        """
        if not hasattr(self, "_emailable"):
            self.load_attributes()
        if not self.is_emailable:
            raise exc.PermissionsError("This user cannot be emailed")
        params = {
            "action": "emailuser", "target": self.name,
            "subject": subject, "text": text
        }
        try:
            token = self._api.tokens['csrf']
        except KeyError:
            self._api.set_token("csrf")
            token = self._api.tokens['csrf']
        params['token'] = token
        if cc:
            params['ccme'] = True
        try:
            return self._api.call(params)
        except exc.CeterachError as e:
            code = e.code
            if code != 'py':
                e = exc.PermissionsError(e)
            raise e from e

    def create(self, password, email="", realname="", logout=True):
        """Try to create a new account on the wiki with the already-specified
        username.

        :type password: str
        :param password: the password that the new account should have.
        :type email: str
        :param email: the email address that the new account should be
                      associated with.
        :type realname: str
        :param realname: the real name that the new account should be
                         associated with.
        :type logout: bool
        :param logout: whether to log the user out right after creating it."""
        raise NotImplementedError
        # return self._api.create_account(self.name, password, email, realname, logout)

    @property
    @decorate
    def is_ip(self) -> bool:
        """Whether this user is an IP user."""
        return "_is_ip"

    @property
    @decorate
    def name(self) -> str:
        """The displayed username or IP address of this user."""
        return "_name"

    @property
    @decorate
    def userpage(self):
        """A Page object that represents this user's userpage."""
        #: :type: ceterach.page.Page
        attr = "_userpage"
        return attr

    @property
    @decorate
    def userid(self) -> int:
        """This user's user id, for internal MediaWiki use."""
        return "_userid"

    @property
    @decorate
    def blockinfo(self) -> dict:
        """Information on the user's current block status.

        This will always return a dict with the keys ``{'by', 'reason',
        'expiry'}``. If the user is not currently blocked, all the values
        will be ``None``.
        """
        return "_blockinfo"

    @property
    @decorate
    def editcount(self) -> int:
        """The number of edits this user has made."""
        return "_editcount"

    @property
    @decorate
    def is_emailable(self) -> bool:
        """Whether this user can be emailed."""
        return "_emailable"

    @property
    @decorate
    def rights(self) -> tuple:
        """The user rights that this user has. This is different from the
        user groups that this user is in, which can be obtained with
        ``.groups``.
        """
        return "_rights"

    @property
    @decorate
    def registration(self) -> datetime:
        """The time that this user registered at."""
        return "_registration"

    @property
    @decorate
    def groups(self) -> list:
        """The user groups that this user is in. This is different from the
        user rights that this user has, which can be obtained with
        ``.rights``.
        """
        return "_groups"

    @property
    @decorate
    def gender(self) -> str:
        """The gender of the user."""
        return "_gender"

    @property
    @decorate
    def exists(self) -> bool:
        """Whether this user account exists."""
        return "_exists"
