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

import re
from hashlib import md5
from datetime import datetime
from time import strftime, gmtime

from . import exceptions as exc
from .revision import Revision
from .utils import isostrptime, blah_decorate

__all__ = ["Page"]


def decorate(meth):
    msg = "Page {0!r} does not exist"
    attr = "title"
    err = exc.NonexistentPageError
    return blah_decorate(meth, msg, attr, err)


class Page:
    """
    This represents a page on a wiki, and has attributes that ease the process
    of getting information about the page.
    """

    def __init__(self, api, title='', pageid=0, follow_redirects=False):
        self._api = api
        if pageid is 0 and title is '':
            err = "You must specify either the 'title' or 'pageid' parameters"
            raise TypeError(err)
        elif pageid is not 0 and title is not '':
            err = "You cannot specify both the 'title' and 'pageid' parameters"
            raise TypeError(err)
        self._title = title
        self._pageid = pageid
        self.follow_redirects = follow_redirects

    def __repr__(self):
        cls_name = type(self).__name__
        text = "{c}(api={self._api!r}, title={self.title!r}, pageid={self.pageid!r}, " \
               "follow_redirects={self.follow_redirects!r})"
        return text.format(c=cls_name, self=self)

    def __eq__(self, other):
        return getattr(other, '_api', None) == self._api and \
               (getattr(other, 'title', None) == self.title or getattr(other, 'pageid', None) == self.pageid)

    def __ne__(self, other):
        return getattr(other, '_api', None) == self._api and \
               (getattr(other, 'title', None) == self.title or getattr(other, 'pageid', None) == self.pageid)

    def identity(self):
        """
        Return a {key: value} that can be used in API queries.

        It should probably return None or raise an exception if nothing useful
        could be found. One day, it will.

        :returns: {"pageids": ...}, {"titles": ...}, or {"revids": ...}
        """
        # TODO: Finish the stuff specified in the docstring
        l = (("titles", "title"),  ("pageids", "pageid"), ("revids", "revid"))
        l = ((k, getattr(self, v, None)) for k, v in l)
        for k, v in l:
            if v: return {k: v}


    def load_attributes(self, res=None):
        """
        Call this to load ``self.__title``, ``._is_redirect``, ``._pageid``,
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
                    correctly are: ``{'inprop': 'protection',
                    'prop': ('info', 'revisions', 'categories'),
                    'rvprop': ('user', 'content')}``

        """
        self.__load(res)
        if self.follow_redirects and self.is_redirect:
            self._title = self.get_redirect_target().title
            del self._content
            self.__load(None)

    def __load(self, res):
        i = self._api.iterator
        prop = ('info', 'revisions', 'categories')
        inprop = ("protection",)
        rvprop = ('ids', 'flags', 'timestamp', 'user', 'comment', 'content')
        kwargs = {"prop": prop, "rvprop": rvprop, "inprop": inprop,
                  "rvlimit": 1, "rvdir": "older"
        }
        if self.title != '':
            kwargs['titles'] = self.title
        elif self.pageid != 0:
            kwargs['pageids'] = self.pageid
        else:
            raise exc.CeterachError("WTF")
        res = res or next(i(1, use_defaults=False, **kwargs))
        # Normalise the page title in case it was entered oddly
        self._title = res['title']
        self._is_redirect = 'redirect' in res
        self._pageid = res.get("pageid", -1)
        if self._pageid < 0:
            if "missing" in res:
                # If it has a negative ID and it's missing, we can still get
                # the namespace...
                self._exists = False
            else:
                # ... but not if it's also invalid
                self._exists = False
                err = "Page {0!r} is invalid"
                raise exc.InvalidPageError(err.format(self.title))
        else:
            self._exists = True
            self._content = res['revisions'][0]["*"]
        self._namespace = res["ns"]
        self._is_talkpage = self._namespace % 2 == 1 # talkpages have odd IDs
        self._protection = {"edit": (None, None),
                            "move": (None, None),
                            "create": (None, None),
        }
        for info in res.get("protection", ''):
            expiry = info['expiry']
            if expiry == 'infinity':
                expiry = getattr(datetime, 'max')
            else:
                expiry = isostrptime(expiry)
            self._protection[info['type']] = info['level'], expiry
        # These last three fields will only be specified if the page exists:
        try:
            self._revision_user = self._api.user(res['revisions'][0]['user'])
            self._revid = res['lastrevid']
            self._revisions = []
        except KeyError:
            pass
        c = self._api.category
        cats = res.get("categories", "")
        self._categories = tuple(c(x['title']) for x in cats)

    def __edit(self, content, summary, minor, bot, force, edittype):
        ident_s = self.identity()
        ident = {k[:-1]: v for (k, v) in ident_s.items()}
        try:
            token = self._api.tokens['edit']
        except KeyError:
            self._api.set_token("edit")
            token = self._api.tokens.get('edit', None)
            if token is None:
                err = "You do not have the edit permission"
                raise exc.PermissionsError(err)
        edit_params = dict(action="edit", text=content, token=token,
                           summary=summary, **ident
        )
        # Apparently English Wikipedia doesn't recognise this anymore
        #edit_params['notbot'] = 1
        edit_params['notminor'] = 1
        edit_params['nocreate'] = 1
        if minor:
            edit_params['minor'] = edit_params.pop("notminor")
        if bot:
            edit_params['bot'] = 1
        if force is False:
            detect_ec = dict(prop="revisions", rvprop="timestamp", **ident_s)
            ec_timestamp_res = next(self._api.iterator(1, **detect_ec))
            if 'missing' in ec_timestamp_res and edittype != 'create':
                err = "Use the 'create' method to create pages"
                raise exc.NonexistentPageError(err)
            elif ec_timestamp_res['ns'] == -1:
                err = "Invalid page titles can't be edited"
                raise exc.InvalidPageError(err)
            if edittype != 'create':
                ec_timestamp = ec_timestamp_res['revisions'][0]['timestamp']
                edit_params['basetimestamp'] = ec_timestamp
                edit_params['starttimestamp'] = strftime("%Y-%m-%dT%H:%M:%SZ", gmtime())
            # Add a checksum to ensure that the text is not corrupted
            edit_params['md5'] = md5(content.encode("utf-8")).hexdigest()
        if edittype == 'append':
            edit_params['appendtext'] = edit_params.pop("text")
        elif edittype == 'prepend':
            edit_params['prependtext'] = edit_params.pop("text")
        elif edittype == 'create':
            edit_params['createonly'] = edit_params.pop("nocreate")
        try:
            res = self._api.call(**edit_params)
        except exc.CeterachError as e:
            # Make the exception more specific
            code = e.code.replace("-anon", "")
            if code in {"articleexists", "editconflict", "pagedeleted"}:
                e = exc.EditConflictError(e)
            elif code in {"noedit", "noimageredirect", "protectedpage",
                          "protectedtitle", "cantcreate"}:
                e = exc.PermissionsError(e)
            elif code == "filtered":
                e = exc.EditFilterError(e)
            elif code == "spamdetected":
                e = exc.SpamFilterError(e)
            elif code != "py":
                e = exc.EditError(e)
            raise e from e  # Suppress context, apparently this works
        if res['edit']['result'] == "Success":
            # Some attributes are now out of date
            # unless it was a nochange
            try:
                del self._content
                self._revid = res['edit']['newrevid']
            except (AttributeError, KeyError):
                pass
            self._exists = True
            self._title = res['edit']['title']  # Normalise the title again
        elif res['edit']['result'] == "Failure":
            for reason in res['edit'].keys() - {"result"}:
                break
            else:
                reason = None
            err = res['edit'][reason] if reason else "Unknown error"
            e = exc.EditError(err, code=reason or "unknownerror")
            if reason == "spamblacklist":
                e = exc.SpamFilterError(err, code=reason)
            raise e
        return res

    def edit(self, content, summary="", minor=False, bot=False, force=False):
        """
        Replace the page's content with *content*. *summary* is the edit
        summary used for the edit. The edit will be marked as minor if *minor*
        is True, and if *bot* is True and the logged-in user has the bot flag,
        it will also be marked as a bot edit.

        Set *force* to True in order to make the edit in spite of edit
        conflicts and nonexistence.

        :type content: str
        :param content: The text with which to replace the page's original
                        content.
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
        return self.__edit(content, summary, minor, bot, force, 'standard')

    def create(self, content, summary="", minor=False, bot=False, force=False):
        """
        Create the page with *content* as the content. *summary* is the edit
        summary used for the edit. The edit will be marked as minor if *minor*
        is True, and if *bot* is True and the logged-in user has the bot flag,
        it will also be marked as a bot edit.

        Set *force* to True in order to make the edit in spite of edit
        conflicts.

        :type content: str
        :param content: The text with which to create the page.
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
        return self.__edit(content, summary, minor, bot, force, 'create')

    def append(self, content, summary="", minor=False, bot=False, force=False):
        """
        Add *content* to the bottom of the page. *summary* is the edit
        summary used for the edit. The edit will be marked as minor if *minor*
        is True, and if *bot* is True and the logged-in user has the bot flag,
        it will also be marked as a bot edit.

        Set *force* to True in order to make the edit in spite of edit
        conflicts or nonexistence.

        :type content: str
        :param content: The text with which to append to the page's original
                        content.
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
        return self.__edit(content, summary, minor, bot, force, 'append')

    def prepend(self, content, summary="", minor=False, bot=False, force=False):
        """
        Add *content* to the top of the page. *summary* is the edit
        summary used for the edit. The edit will be marked as minor if *minor*
        is True, and if *bot* is True and the logged-in user has the bot flag,
        it will also be marked as a bot edit.

        Set *force* to True in order to make the edit in spite of edit
        conflicts or nonexistence.

        :type content: str
        :param content: The text with which to prepend to the page's original
                        content.
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
        return self.__edit(content, summary, minor, bot, force, 'prepend')

    def move(self, target, reason, talk=False, subpages=False,
             redirect=True):
        """
        Move the page to a new title, *target*.

        :type target: str
        :param target: Title you want to rename the page to.
        :type reason: str
        :param reason: The reason for the move.
        :type talk: bool
        :param talk: Move the talk page too, if set to True.
        :type subpages: bool
        :param subpages: Move subpages too, if set to True.
        :type redirect: bool
        :param redirect: Leave a redirect behind, if set to True.
        :returns: A dictionary containing the API query result.
        """
        move_params = {"action": "move", "from": self.title,
                       "to": target, "reason": reason,
                       "movetalk": talk, "movesubpages": subpages,
                       "noredirect": not redirect,
        }
        move_params = {k: v for (k, v) in move_params.items() if v}
        move_params['token'] = self._api.tokens['move']
        if move_params['token'] is None:
            self._api.set_token("move")
            if move_params['token'] is None:
                err = "You do not have the move permission"
                raise exc.PermissionsError(err)
        #allowed = ("movetalk", "movesubpages", "noredirect", "watch", "unwatch")
        return self._api.call(**move_params)

    def delete(self, reason=""):
        """
        Delete the page.

        :type reason: str
        :param reason: The reason for the deletion.
        :returns: A dictionary containing the API query result
        """
        stuff = {"action": "delete", "title": self.title}
        if reason:
            stuff['reason'] = reason
        stuff['token'] = self._api.tokens['delete']
        if not stuff['token']:
            self._api.set_token("delete")
            if not self._api.tokens['delete']:
                err = "You do not have the delete permission"
                raise exc.PermissionsError(err)
            stuff['token'] = self._api.tokens['delete']
        return self._api.call(stuff)

    def undelete(self, reason=""):
        """
        Undelete the page.

        :type reason: str
        :param reason: The reason for the undeletion.
        :returns: A dictionary containing the API query result
        """
        stuff = {"action": "undelete", "title": self.title}
        if reason:
            stuff['reason'] = reason
        stuff['token'] = self._api.tokens['undelete']
        if not stuff['token']:
            self._api.set_token("undelete")
            if not self._api.tokens['undelete']:
                err = "You do not have the delete permission"
                raise exc.PermissionsError(err)
            stuff['token'] = self._api.tokens['undelete']
        return self._api.call(stuff)

    def from_revid(self, revid):
        """
        Returns a Page object by extracting information from the given revid.

        This method does not follow redirects, and the very process of calling
        the method makes an API query.

        :type revid: int
        :param revid: The revision ID corresponding to the page being requested.
        :returns: A page.
        """
        kwargs = {"prop": ("info", "revisions", "categories"),
                  "inprop": "protection",
                  "rvprop": ("user", "content"),
                  "revids": revid,
        }
        res = self._api.iterator(use_defaults=False, **kwargs)
        p = type(self)(self._api, "some random title")
        p.load_attributes(tuple(res)[0])
        return p

    def load_revisions(self, num=float("inf")):
        """Call this to populate self.revisions. Specify the *num* parameter
        to limit it to *num* revisions, in reverse chronological order."""
        kwargs = {"prop": "revisions",
                  "rvprop": ('ids', 'flags', 'timestamp',
                             'user', 'comment', 'content'),
                  "rvlimit": 'max' if num == float("inf") else num,
                  "rvdir": "older",
                  "rvstartid": self.revid,
        }
        kwargs.update(self.identity())
        res = self._api.call(use_defaults=False, **kwargs)
        revs = tuple(res['query']['pages'].values())[0]['revisions']
        for r in revs:
            revision_obj = Revision(self._api, r['revid'])
            filler = {"pageid": self.pageid}
            filler['revisions'] = (r,)
            revision_obj.load_attributes(filler)
            self._revisions.append(revision_obj)

    def toggle_talk(self, follow_redirects=None):
        """
        Return a page with its namespace switched to or from the talk
        namespace.

        :type follow_redirects: bool
        :param follow_redirects: If set to anything other than None (the
                                 default), this will be passed to the new Page
                                 object's constructor. Otherwise, it will be
                                 set to the one passed to its own constructor.
        :returns: The page that's either the talk or non-talk version of the
                  current page.
        :raises: exc.InvalidPageError
        """
        ns = self._api.namespaces[self.namespace]
        if self.namespace < 0:
            err = "Pages in the {0!r} namespace do not have talk pages"
            raise exc.InvalidPageError(err.format(ns))
        if self.is_talkpage:
            # Talk -> Content
            new_ns = self.namespace - 1
            new_title = (":" if new_ns else "") + self.title.partition(":")[-1]
        else:
            # Content -> Talk
            new_ns = self.namespace + 1
            if not self.namespace:
                new_title = ":" + self.title
            else:
                new_title = ":" + self.title.partition(":")[-1]
        new_ns_prefix = self._api.namespaces[new_ns]
        full_title = new_ns_prefix + new_title
        if follow_redirects is None:
            follow_redirects = self.follow_redirects
        return self._api.page(full_title, follow_redirects)

    @property
    def title(self) -> str:
        """
        Returns the page's title. If self.load_attributes() was not called
        prior to the execution of this method, the result will be equal to the
        *title* parameter passed to the constructor. Otherwise, it will be
        normalised.

        :returns: The page's title.
        """
        return self._title

    @property
    def pageid(self) -> int:
        """
        An integer ID representing the page.

        :returns: The page's ID.
        """
        return self._pageid

    @property
    @decorate
    def content(self) -> str:
        """
        Returns the page content, which is cached if you try to get this
        attribute again.

        If the page does not exist, the method raises a NonexistentPageError.

        :returns: The page content
        :raises: NonexistentPageError
        """
        return "_content"

    @property
    @decorate
    def exists(self) -> bool:
        """
        Check the existence of the page.

        :returns: True if the page exists, False otherwise
        """
        return "_exists"

    @property
    @decorate
    def is_talkpage(self) -> bool:
        """
        Check if this page is in a talk namespace.

        :returns: True if the page is in a talk namespace, False otherwise
        """
        return "_is_talkpage"

    @property
    @decorate
    def revision_user(self):
        """
        Returns the username or IP of the last user to edit the page.

        :returns: A User object
        :raises: NonexistentPageError, if the page doesn't exist or is invalid.
        """
        #: :type: ceterach.user.User
        attr = "_revision_user"
        return attr

    def get_redirect_target(self):
        """
        Gets the Page object for the target this Page redirects to.

        If this Page doesn't exist, or is invalid, it will
        raise a NonexistentPageError, or InvalidPageError respectively. If the
        page isn't a redirect, it will raise a RedirectError.

        :returns: Page object that represents the redirect target.
        :raises: NonexistentPageError, InvalidPageError, RedirectError
        """
        if not self.exists:
            raise exc.NonexistentPageError("Page does not exist")
        if not self.is_redirect:
            raise exc.RedirectError("Page is not a redirect")
        if hasattr(self, "_redirect_target"):
            return self._redirect_target
        redirect_regex = re.compile(r"#redirect\s*?\[\[(.+?)\]\]", re.I)
        haspage = redirect_regex.match(self.content)
        if haspage:
            target = haspage.group(1)
            self._redirect_target = self._api.page(target)
            return self._redirect_target
        raise exc.RedirectError("Could not determine redirect target")

    @property
    @decorate
    def is_redirect(self) -> bool:
        """
        :returns: True if the page is a redirect, False if the Page isn't or
                  doesn't exist.
        """
        return "_is_redirect"

    @property
    @decorate
    def namespace(self) -> int:
        """
        :returns: An integer representing the Page's namespace.
        """
        return "_namespace"

    @property
    @decorate
    def protection(self) -> dict:
        """
        Get the protection levels on the page.

        :returns: A dict representing the page's protection level. The keys
                  are, by default, 'edit', 'create', and 'move'. If the wiki
                  is configured to have other protection types, those types
                  will also be included in the keys. The values can be
                  ``(None, None)`` (no restriction for that action) or
                  ``(level, expiry)``:

                  - ``level`` is the userright needed to perform the action
                    (``"autoconfirmed"``, for example)
                  - ``expiry`` is the expiration time of the restriction. This
                    will either be None, or a datetime at which the protection
                    will expire.
        """
        return "_protection"

    @property
    @decorate
    def revid(self) -> int:
        """
        :returns: An integer representing the Page's current revision ID.
        """
        return "_revid"

    @property
    @decorate
    def categories(self) -> tuple:
        """A tuple containing the categories that the page can be found in."""
        return "_categories"

    @property
    def revisions(self) -> tuple:
        """A tuple containing the page's revisions, from newest to oldest."""
        return tuple(self._get_revs())

    @decorate
    def _get_revs(self):
        return "_revisions"
